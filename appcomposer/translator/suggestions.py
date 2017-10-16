import sys
import hashlib
import random
import traceback
import datetime

from xml.etree import ElementTree

import pydeepl
import goslate
import requests

from celery.utils.log import get_task_logger

from sqlalchemy import func
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

        existing_suggestions, remaining_texts = self.existing_translations(texts, language, origin_language)
        if remaining_texts:
            new_suggestions = self._translate(remaining_texts, language, origin_language)
            for human_key, value in new_suggestions.iteritems():
                new_suggestion = TranslationExternalSuggestion(engine = self.name, human_key = human_key, language = language, origin_language = origin_language, value = value)
                db.session.add(new_suggestion)
                existing_suggestions[human_key] = { value : 1 }
            try:
                db.session.commit()
            except IntegrityError:
                traceback.print_exc()
                db.session.rollback()
            except:
                traceback.print_exc()
                db.session.rollback()
                db.session.remove()
                raise
            db.session.remove()
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
        hashed_texts_per_text = { text: hashlib.md5(text.encode('utf8')).hexdigest() for text in texts }
        text_per_hash = { v:k for (k, v) in hashed_texts_per_text.items() }
        hashed_texts = list(hashed_texts_per_text.values())
        
        if hashed_texts:
            suggestions = db.session.query(TranslationExternalSuggestion).filter(TranslationExternalSuggestion.engine == self.name, TranslationExternalSuggestion.human_key_hash.in_(hashed_texts), TranslationExternalSuggestion.language == language, TranslationExternalSuggestion.origin_language == origin_language).all()
        else:
            suggestions = []
        
        remaining_texts = texts[:]
        existing_suggestions = {}
        for suggestion in suggestions:
            human_key = text_per_hash.get(suggestion.human_key_hash)
            existing_suggestions[human_key] = { suggestion.value : 1 }
            if human_key in remaining_texts:
                remaining_texts.remove(human_key)
        
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

    @property
    def languages(self):
        # as of October 2017
        return list(["af", "sq", "am", "ar", "hy", "az", "eu", "be", "bn", "bs", "bg", "ca", "zh", "zh", "co", "hr", "cs", "da", "nl", "en", "eo", "et", "fi", "fr", "fy", "gl", "ka", "de", "el", "gu", "ht", "ha", "iw", "hi", "hu", "is", "ig", "id", "ga", "it", "ja", "jw", "kn", "kk", "km", "ko", "ku", "ky", "lo", "la", "lv", "lt", "lb", "mk", "mg", "ms", "ml", "mt", "mi", "mr", "mn", "my", "ne", "no", "ny", "ps", "fa", "pl", "pt", "pa", "ro", "ru", "sm", "gd", "sr", "st", "sn", "sd", "si", "sk", "sl", "so", "es", "su", "sw", "sv", "tl", "tg", "ta", "te", "th", "tr", "uk", "ur", "uz", "vi", "cy", "xh", "yi", "yo", "zu"]) + ['se', 'sh', 'he'] # For some reason, there are translations in these two languages

    def _translate(self, texts, language, origin_language = 'en'):
        """ [ 'Hello' ], 'es' => { 'Hello' : 'Hola' } """
        # We don't provide anything and asynchronously populate the database
        return {}

class DeeplTranslator(AbstractTranslator):
    name = 'deepl'

    @property
    def languages(self):
        return [ lang.lower() for lang in SUPPORTED_DEEPL_LANGUAGES ]

    def _translate(self, texts, language, origin_language = 'en'):
        """ [ 'Hello' ], 'es' => { 'Hello' : 'Hola' } """
        # We don't provide anything and asynchronously populate the database
        return {}

microsoft_translator = MicrosoftTranslator()
google_translator = GoogleTranslator()
deepl_translator = DeeplTranslator()

TRANSLATORS = [
    microsoft_translator,
    google_translator,
    deepl_translator,
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
                    traceback.print_stack()
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


def _load_generic_suggestions_by_lang(active_messages, language, origin_language, engine, translation_func, bulk_messages):
    if origin_language is None:
        origin_language = ORIGIN_LANGUAGE

    logger.info("Using %s to use %s" % (engine, language))

    existing_suggestion_hashes = set([ human_key_hash for human_key_hash, in db.session.query(TranslationExternalSuggestion.human_key_hash).filter_by(engine = engine, language = language, origin_language = origin_language).all() ])
    active_message_hashes = { hashlib.md5(text.encode('utf8')).hexdigest(): text for text in active_messages }

    missing_suggestion_hashes = set(active_message_hashes.keys()) - existing_suggestion_hashes
    missing_suggestions = [ active_message_hashes[missing_hash] for missing_hash in missing_suggestion_hashes ]
    print "Language:", language
    print "Missing ",  len(missing_suggestions), ":", missing_suggestions[:5], "..."
    random.shuffle(missing_suggestions)
    counter = 0

    if bulk_messages:
        results = translation_func(missing_suggestions, language)
        for message, translated in results.items():
            suggestion = TranslationExternalSuggestion(engine = engine, human_key = message, language = language, origin_language = origin_language, value = translated)
            db.session.add(suggestion)
            counter += 1

        if results:
            try:
                db.session.commit()
            except:
                db.session.rollback()
                raise
        else:
            return False, counter

    else:

        for message in missing_suggestions:
            if message.strip() == '':
                continue

            try:
                translated = translation_func(message, language)
            except Exception as e:
                logger.warning("%s stopped in pos %s with exception: %s" % (engine, counter, e), exc_info = True)
                return False, counter
            else:
                counter += 1

            if translated:
                suggestion = TranslationExternalSuggestion(engine = engine, human_key = message, language = language, origin_language = origin_language, value = translated)
                db.session.add(suggestion)
                try:
                    db.session.commit()
                except:
                    db.session.rollback()
                    raise
            else:
                logger.warning("%s returned %r for message %r in pos %s. Stopping." % (engine, translated, message, counter))
                return False, counter

    return True, counter

def _gtranslate(message, language):
    gs = goslate.Goslate()
    return gs.translate(message, language)

def _deepltranslate(message, language):
    return pydeepl.translate(message, language.upper(), from_lang='EN')

def _mstranslate(messages, language):
    return microsoft_translator._translate(messages, language)

SUPPORTED_DEEPL_LANGUAGES = ['DE', 'EN', 'ES', 'FR', 'IT', 'NL', 'PL']

def load_deepl_suggestions_by_lang(active_messages, language, origin_language = None):
    """ Attempt to translate all the messages to a language """
    if language.upper() not in SUPPORTED_DEEPL_LANGUAGES:
        return True, 0

    if language.upper() == 'EN':
        return True, 0

    return _load_generic_suggestions_by_lang(active_messages, language, origin_language, 'deepl', translation_func = _deepltranslate, bulk_messages=False)

def load_google_suggestions_by_lang(active_messages, language, origin_language = None):
    """ Attempt to translate all the messages to a language """
    if language == 'en':
        return True, 0

    return _load_generic_suggestions_by_lang(active_messages, language, origin_language, 'google', translation_func = _gtranslate, bulk_messages=False)

def load_microsoft_suggestions_by_lang(active_messages, language, origin_language = None):
    """ Attempt to translate all the messages to a language """
    if language == 'en':
        return True, 0

    found = False
    for ms_language in microsoft_translator.languages:
        if ms_language == language:
            found = True

    if not found:
        return True, 0 # Focus on those not available in Microsoft

    last_month = datetime.datetime.utcnow() - datetime.timedelta(days=32)

    row = db.session.query(func.sum(func.char_length(TranslationExternalSuggestion.value))).filter(TranslationExternalSuggestion.origin_language == u'en', TranslationExternalSuggestion.engine==u'microsoft', TranslationExternalSuggestion.created>=last_month).first()
    # we don't have the right size of the human_key. we can use the value, but it's not accurate.
    # we have 2M per month. So we select 1.5M max (which is around 1.7M real)
    if row[0] > 1500000:
        return False, 0

    return _load_generic_suggestions_by_lang(active_messages, language, origin_language, 'microsoft', translation_func = _mstranslate, bulk_messages=True)


# ORDERED_LANGUAGES: first the semi official ones (less likely to have translations in Microsoft Translator API), then the official ones and then the rest
ORDERED_LANGUAGES = SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES + OFFICIAL_EUROPEAN_UNION_LANGUAGES + OTHER_LANGUAGES

def _load_all_suggestions(from_language, to_languages_per_category, load_function, engine):
    active_messages = set([ value for value, in db.session.query(ActiveTranslationMessage.value).filter(TranslationBundle.language == '{0}_ALL'.format(from_language), ActiveTranslationMessage.bundle_id == TranslationBundle.id).all() ])
    active_messages = list(active_messages)
    random.shuffle(active_messages)

    total_counter = 0

    should_continue = True

    message_size = 100 # send messages from 100 in 100

    for block_number in range(len(active_messages) / message_size + 1):
        current_block = active_messages[block_number * message_size: (block_number + 1 ) * message_size]

        for to_languages in to_languages_per_category:
            #
            # per category are first the official and co-official ones, then the others
            #
            to_languages = list(to_languages)
            random.shuffle(to_languages)

            for language in to_languages:
                should_continue, counter = load_function(current_block, language)
                total_counter += counter
                if total_counter > 50000:
                    should_continue = False
                    logger.info("Stopping the %s suggestions API after performing %s queries until the next cycle" % (engine, total_counter))
                    break

                if not should_continue:
                    logger.info("Stopping the %s suggestions API until the next cycle" % engine)
                    # There was an error: keep in the next iteration ;-)
                    break

            if not should_continue:
                break

        if not should_continue:
            break

def load_all_deepl_suggestions():
    # First try to create suggestions from English to all the languages

    languages_per_category = [ SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES + OFFICIAL_EUROPEAN_UNION_LANGUAGES, OTHER_LANGUAGES ]

    _load_all_suggestions('en', languages_per_category, load_function = load_deepl_suggestions_by_lang, engine='deepl')


def load_all_google_suggestions():
    # First try to create suggestions from English to all the languages

    languages_per_category = [ SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES + OFFICIAL_EUROPEAN_UNION_LANGUAGES, OTHER_LANGUAGES ]

    _load_all_suggestions('en', languages_per_category, load_function = load_google_suggestions_by_lang, engine='google')

def load_all_microsoft_suggestions():
    # First try to create suggestions from English to all the languages

    languages_per_category = [ SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES + OFFICIAL_EUROPEAN_UNION_LANGUAGES, OTHER_LANGUAGES ]

    _load_all_suggestions('en', languages_per_category, load_function = load_microsoft_suggestions_by_lang, engine='microsoft')


def load_google_paid():
    # priority_languages = [u'sh', u'se', u'mk', u'lb', u'my', u'bs', u'be', u'sr', u'id', u'ja', u'zh', u'hi', u'no', u'uk', u'tr', u'ar', u'de']
    priority_languages = [u'sh', u'mk', u'lb', u'my', u'bs', u'be', u'sr', u'id', u'ja', u'zh', u'hi', u'no', u'uk', u'tr', u'ar', u'de'] + [ unicode(lang) for lang in SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES + OFFICIAL_EUROPEAN_UNION_LANGUAGES + OTHER_LANGUAGES if lang not in ['en', 'se'] ]

    active_messages = set([ value for value, in db.session.query(ActiveTranslationMessage.value).filter(TranslationBundle.language == u'en_ALL', TranslationBundle.target == u'ALL', ActiveTranslationMessage.bundle_id == TranslationBundle.id).all() ])
    active_message_by_hash = { unicode(hashlib.md5(text.encode('utf8')).hexdigest()): text for text in active_messages }
    print "Total of", len(active_messages), "messages in English"

    total_char = 0

    for lang in priority_languages:
        existing_hashes = { human_key_hash for human_key_hash, in db.session.query(TranslationExternalSuggestion.human_key_hash).filter(TranslationExternalSuggestion.origin_language == u'en', TranslationExternalSuggestion.language == lang, TranslationExternalSuggestion.engine == u'google').all() }
        missing_hashes = set(active_message_by_hash.keys()) - existing_hashes

        lang_chars = sum([ len(active_message_by_hash[msg_hash]) for msg_hash in missing_hashes ])
        total_char += lang_chars

        print " + ",lang, "missing", len(missing_hashes), "messages. Total characters:", lang_chars

        block_size = 50

        if not missing_hashes:
            continue

        missing_hashes = list(missing_hashes)

        for block_number in range(1 + (len(missing_hashes) / block_size)):
            initial_pos = block_size * block_number
            final_pos = block_size * (block_number + 1)
            current_block_hashes = missing_hashes[initial_pos:final_pos]
            current_block_msgs = [ active_message_by_hash[msg_hash] for msg_hash in current_block_hashes ]

            print "   - Translating {}:{}...".format(initial_pos, final_pos)

            from google.cloud import translate
            client = translate.Client()

            try:
                translated_results = client.translate(current_block_msgs, target_language=lang, source_language='en')
            except Exception as e:

                traceback.print_exc()
                if u"User Rate Limit Exceeded" in unicode(e):
                    return
                continue

            for translated_result in translated_results:
                try:
                    original_message = translated_result['input']
                    translated_text = translated_result['translatedText']
                except:
                    print("Error parsing:", translated_result)
                    traceback.print_exc()
                    continue

                suggestion = TranslationExternalSuggestion(engine=u'google', human_key=original_message, language=lang, origin_language=u'en', value=translated_text)
                db.session.add(suggestion)

            db.session.commit()
            db.session.remove()

    print "Total:", total_char

if __name__ == '__main__':
    with app.app_context():
        load_google_paid()
