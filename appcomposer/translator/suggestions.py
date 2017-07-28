import sys
import hashlib
import random
import traceback

from xml.etree import ElementTree

import goslate
import requests


from celery.utils.log import get_task_logger

from sqlalchemy.exc import IntegrityError

from appcomposer.application import app
from appcomposer.db import db
from appcomposer.models import TranslationExternalSuggestion, ActiveTranslationMessage, TranslationBundle

from appcomposer.languages import SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES, OFFICIAL_EUROPEAN_UNION_LANGUAGES, OTHER_LANGUAGES

logger = get_task_logger(__name__)

class AbstractTranslator(object):

    def __init__(self):
        if self.name not in app.config.get('EXTERNAL_TRANSLATORS'):
            self.enabled = False
        else:
            self.enabled = True

        self.options = app.config.get('EXTERNAL_TRANSLATORS', {}).get(self.name)

    def translate_texts(self, texts, language, origin_language = 'en'):
        if not self.enabled:
            return {}

        language = language.split('_')[0]

        existing_suggestions, remaining_texts = self.existing_translations(texts, language)
        if remaining_texts:
            new_suggestions = self._translate(remaining_texts, language, origin_language)
            for human_key, value in new_suggestions.iteritems():
                new_suggestion = TranslationExternalSuggestion(engine = self.name, human_key = human_key, language = language, origin_language = origin_language, value = value)
                db.session.add(new_suggestion)
                existing_suggestions[human_key] = { value : 1 }
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
            except:
                db.session.rollback()
                raise
        return existing_suggestions

    def existing_translations(self, texts, language, origin_language = 'en'):
        """ Given a list of texts, and a language, this returns a tuple as:
        
        existing_suggestions, remaining_texts

        The first is a dictionary which maps the texts to the existing suggestions. E.g. ( { 'Hello' : { 'Hi' : 1} } ).
        The second is a dictionary which provides which texts have not been provided. E.g. ( ['Hello'] )
        """
        if not self.enabled:
            return {}, texts[:]
        

        language = language.split('_')[0]
        hashed_texts = [ hashlib.md5(text.encode('utf8')).hexdigest() for text in texts ]
        
        if hashed_texts:
            suggestions = db.session.query(TranslationExternalSuggestion).filter(TranslationExternalSuggestion.engine == self.name, TranslationExternalSuggestion.human_key_hash.in_(hashed_texts), TranslationExternalSuggestion.language == language, TranslationExternalSuggestion.origin_language == origin_language).all()
        else:
            suggestions = []

        remaining_texts = texts[:]
        existing_suggestions = {}
        for suggestion in suggestions:
            existing_suggestions[suggestion.human_key] = { suggestion.value : 1 }
            if suggestion.human_key in remaining_texts:
                remaining_texts.remove(suggestion.human_key)

        return existing_suggestions, remaining_texts

class MicrosoftTranslator(AbstractTranslator):
    name = 'microsoft'

    def __init__(self):
        super(MicrosoftTranslator, self).__init__()
        self.client_secret = None

        if self.options is not None:
            self.client_secret = self.options.get('client_secret')
            if self.client_secret is None:
                raise ValueError("Misconfigured application. If you use the Microsoft Translator, provide a client_secret")

        self._languages = None

    @property
    def languages(self):
        if self._languages is not None:
            return self._languages
        if self.client_secret is None:
            self._languages = []
        try:
            self._languages = self._get_languages()
        except Exception:
            traceback.print_exc()
            return []
        return self._languages

    def _get_token(self):
        token_service_url = 'https://api.cognitive.microsoft.com/sts/v1.0/issueToken'

        request_headers = {'Ocp-Apim-Subscription-Key': self.client_secret}

        response = requests.post(token_service_url, headers=request_headers)
        response.raise_for_status()

        return response.content

    def _get_languages(self):
        headers = {"Authorization ": 'Bearer ' + self._get_token() }
        url = "https://api.microsofttranslator.com/V2/Http.svc/GetLanguagesForTranslate"
        languages = requests.get(url, headers = headers)
        root = ElementTree.fromstring(languages.text.encode('utf-8'))
        return [ e.text for e in root.findall("{http://schemas.microsoft.com/2003/10/Serialization/Arrays}string") ]

    def _translate_messages(self, messages, language, origin_language):
        request_root = ElementTree.fromstring("""<GetTranslationsArrayRequest>
          <AppId></AppId>
          <From>{origin}</From>
          <Options>
          </Options>
          <Texts>
          </Texts>
          <To>{lang}</To>
          <MaxTranslations>1000</MaxTranslations>
        </GetTranslationsArrayRequest>""".format(lang=language, origin=origin_language))

        texts = request_root.find("Texts")
        for message in messages:
            subelement = ElementTree.SubElement(texts, '{http://schemas.microsoft.com/2003/10/Serialization/Arrays}string')
            subelement.text = message

        data = ElementTree.tostring(request_root)

        url = "https://api.microsofttranslator.com/V2/Http.svc/GetTranslationsArray"
        headers = {
            'Authorization': 'Bearer ' + self._get_token(),
            'Content-Type': 'application/xml'
        }
        translation_data = requests.post(url, data=data, headers = headers).text
        root = ElementTree.fromstring(translation_data.encode('utf8'))
        return [ e.text for e in root.findall(".//{http://schemas.datacontract.org/2004/07/Microsoft.MT.Web.Service.V2}TranslatedText") ]

    def _translate(self, texts, language, origin_language = 'en'):
        """ [ 'Hello' ], 'es' => { 'Hello' : 'Hola' } """
        if self.client_secret is None:
            return {}

        if language not in self.languages:
            return {}

        unique_texts = list(set(texts))
        
        slices = [
            # the size of a slice can't be over 10k characters in theory (we try to keep them under 5k in practice)
            # Neither more than 10 elements per slice (!!!)
            # [ element1, element2, element3 ...]
            [],
        ]
        current_slice = slices[0]

        for text in unique_texts:
            current_slice.append(text)
            if len(u''.join(current_slice).encode('utf8')) > 2000 or len(current_slice) == 10:
                current_slice = []
                slices.append(current_slice)

        app.logger.debug("Texts splitted in {} slices".format(len(slices)))
        for pos, slice in enumerate(slices):
            app.logger.debug("  slice: {}: {} characters".format(pos, len(''.join(slice).encode('utf8'))))
        
        ms_translations = {}
        errors = False
        for current_slice in slices:
            if current_slice:
                app.logger.debug("Translating %r to %r using Microsoft Translator API" % (current_slice, language))
                try:
                    current_ms_translations = self._translate_messages(messages = current_slice, language = language, origin_language=origin_language)
                except Exception as e:
                    traceback.print_exc()
                    app.logger.warn("Error translating using Microsoft Translator API: %s" % e, exc_info = True)
                    errors = True
                    continue
                else:
                    for current_text, current_translation in zip(current_slice, current_ms_translations):
                        ms_translations[current_text] = current_translation
                    app.logger.debug("Translated %s sentences using Microsoft Translator API" % len(current_ms_translations))

        if errors and not ms_translations:
            return {}
        
        sys.stdout.flush()
        sys.stderr.flush()
        return ms_translations

class GoogleTranslator(AbstractTranslator):
    name = 'google'

    def _translate(self, texts, language, origin_language = 'en'):
        """ [ 'Hello' ], 'es' => { 'Hello' : 'Hola' } """
        # We don't provide anything and asynchronously populate the database
        return {}

TRANSLATORS = [ 
    MicrosoftTranslator(), 
    GoogleTranslator() 
]

def translate_texts(texts, language, origin_language = 'en'):
    """ translate_texts(['Hello', 'Bye'], 'es') -> { 'Hello' : {'Hola' : 1}, 'Bye' : { 'Adios' : 1}} """
    translations = {}
    for key in texts:
        translations[key] = {
            # 'potential1': 1,
            # 'potential2': 2,
        }

    for translator in TRANSLATORS:
        current_translations = translator.translate_texts(texts, language, origin_language)
        for key, values in current_translations.iteritems():
            if key not in translations:
                try:
                    print(u"Corrupt translation. translator {} returned key {} not found in the original".format(translator, key))
                except:
                    traceback.print_exc()
                continue
            for value, weight in values.iteritems():
                if value not in translations[key]:
                    translations[key][value] = 0
                translations[key][value] += weight

    return translations

def existing_translations(texts, language, origin_language = 'en'):
    translations = {
    #    'Hello' : {
    #        'Hola' : 30,
    #        'Buenas' : 1,
    #    }
    }
    remaining_texts = []

    for translator in TRANSLATORS:
        current_translations, current_remaining_texts = translator.existing_translations(texts, language, origin_language)
        for remaining_text in current_remaining_texts:
            if remaining_text not in translations:
                remaining_texts.append(remaining_text)
        for translation_key, translation_values in current_translations.iteritems():
            if translation_key in remaining_texts:
                remaining_texts.remove(translation_key)

            if translation_key not in translations:
                translations[translation_key] = {}

            for value, weight in translation_values.iteritems():
                if value not in translations[translation_key]:
                    translations[translation_key] = { value : 0 }
                translations[translation_key][value] += weight

    return translations, remaining_texts

ORIGIN_LANGUAGE = 'en'

def load_google_suggestions_by_lang(active_messages, language, origin_language = None):
    """ Attempt to translate all the messages to a language """
    
    if origin_language is None:
        origin_language = ORIGIN_LANGUAGE

    gs = goslate.Goslate()
    logger.info("Using Google Translator to use %s" % language)

    existing_suggestions = set([ human_key for human_key, in db.session.query(TranslationExternalSuggestion.human_key).filter_by(engine = 'google', language = language, origin_language = origin_language).all() ])

    missing_suggestions = active_messages - existing_suggestions
    print "Language:", language
    print "Missing ",  len(missing_suggestions), ":", list(missing_suggestions)[:5], "..."
    missing_suggestions = list(missing_suggestions)
    random.shuffle(missing_suggestions)
    counter = 0

    for message in missing_suggestions:
        if message.strip() == '':
            continue

        try:
            translated = gs.translate(message, language)
        except Exception as e:
            logger.warning("Google Translate stopped in pos %s with exception: %s" % (counter, e), exc_info = True)
            return False, counter
        else:
            counter += 1

        if translated:
            suggestion = TranslationExternalSuggestion(engine = 'google', human_key = message, language = language, origin_language = origin_language, value = translated)
            db.session.add(suggestion)
            try:
                db.session.commit()
            except:
                db.session.rollback()
                raise
        else:
            logger.warning("Google Translate returned %r for message %r in pos %s. Stopping." % (translated, message, counter))
            return False, counter

    return True, counter


# ORDERED_LANGUAGES: first the semi official ones (less likely to have translations in Microsoft Translator API), then the official ones and then the rest
ORDERED_LANGUAGES = SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES + OFFICIAL_EUROPEAN_UNION_LANGUAGES + OTHER_LANGUAGES

def _load_all_google_suggestions(from_language, to_languages_per_category):
    active_messages = set([ value for value, in db.session.query(ActiveTranslationMessage.value).filter(TranslationBundle.language == '{0}_ALL'.format(from_language), ActiveTranslationMessage.bundle_id == TranslationBundle.id).all() ])
    
    total_counter = 0

    should_continue = True

    for to_languages in to_languages_per_category:
        # 
        # per category are first the official and co-official ones, then the others
        # 
        to_languages = list(to_languages)
        random.shuffle(to_languages)
        
        for language in to_languages:
            should_continue, counter = load_google_suggestions_by_lang(active_messages, language)
            total_counter += counter
            if total_counter > 1000:
                should_continue = False
                logger.info("Stopping the google suggestions API after performing %s queries until the next cycle" % total_counter)
                break

            if not should_continue:
                logger.info("Stopping the google suggestions API until the next cycle")
                # There was an error: keep in the next iteration ;-)
                break

        if not should_continue:
            break


def load_all_google_suggestions():
    # First try to create suggestions from English to all the languages

    languages_per_category = [ SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES + OFFICIAL_EUROPEAN_UNION_LANGUAGES, OTHER_LANGUAGES ]

    _load_all_google_suggestions('en', languages_per_category)

    # Then, try to create suggestions all the languages to English for developers
    # 
    # Skipped: we already have Microsoft for that.
    # 
    # for language in ORDERED_LANGUAGES:
    #     _load_all_google_suggestions(language, [['en']])

if __name__ == '__main__':
    with app.app_context():
        print existing_translations(["Hello", "Bye", "Good morning", "This was never stored"], 'es')
        print translate_texts(["Hello", "Bye", "Good morning"], 'es')

