import hashlib
import traceback
from microsofttranslator import Translator as MSTranslator, TranslateApiException as MSTranslatorApiException, ArgumentOutOfRangeException

from sqlalchemy.exc import IntegrityError

from appcomposer.application import app
from appcomposer.db import db
from appcomposer.models import TranslationExternalSuggestion

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

        suggestions = db.session.query(TranslationExternalSuggestion).filter(TranslationExternalSuggestion.engine == self.name, TranslationExternalSuggestion.human_key_hash.in_(hashed_texts), TranslationExternalSuggestion.language == language, TranslationExternalSuggestion.origin_language == origin_language).all()

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
        if self.options is not None:
            client_id = self.options.get('client_id')
            client_secret = self.options.get('client_secret')
            if client_id is None or client_secret is None:
                raise ValueError("Misconfigured application. If you use the Microsoft Translator, provide a client_id and a client_secret")
            self.client = MSTranslator(client_id = client_id, client_secret = client_secret)
        else:
            self.client = None

        self._languages = None

    @property
    def languages(self):
        if self._languages is not None:
            return self._languages
        if self.client is None:
            self._languages = []
        try:
            self._languages = self.client.get_languages()
        except MSTranslatorApiException:
            return []
        except Exception:
            return []
        return self._languages

    def _translate(self, texts, language, origin_language = 'en'):
        """ [ 'Hello' ], 'es' => { 'Hello' : 'Hola' } """
        if self.client is None:
            return {}

        if language not in self.languages:
            return {}
        
        slices = [
            # the size of a slice can't be over 10k characters in theory (we try to keep them under 5k in practice)
            # [ element1, element2, element3 ...]
            [],
        ]
        current_slice = slices[0]

        for text in texts:
            current_slice.append(text)
            if len(u''.join(current_slice).encode('utf8')) > 2000:
                current_slice = []
                slices.append(current_slice)

        app.logger.debug("Texts splitted in {} slices".format(len(slices)))
        for pos, slice in enumerate(slices):
            app.logger.debug("  slice: {}: {} characters".format(pos, len(''.join(slice).encode('utf8'))))
        
        ms_translations = []
        errors = False
        for current_slice in slices:
            if current_slice:
                app.logger.debug("Translating %r to %r using Microsoft Translator API" % (current_slice, language))
                try:
                    current_ms_translations = self.client.translate_array(texts = current_slice, to_lang = language, from_lang = origin_language)
                except (MSTranslatorApiException, ArgumentOutOfRangeException, ValueError, Exception) as e:
                    traceback.print_exc()
                    app.logger.warn("Error translating using Microsoft Translator API: %s" % e, exc_info = True)
                    errors = True
                    continue
                else:
                    ms_translations.extend(list(current_ms_translations))
                    app.logger.debug("Translated %s sentences using Microsoft Translator API" % len(current_ms_translations))

        if errors and not ms_translations:
            return {}
        
        translations = {}
        for text, translation in zip(texts, ms_translations):
            translated_text = translation.get('TranslatedText')
            if translated_text:
                translations[text] = translated_text
        
        return translations

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
        translations[key] = {}

    for translator in TRANSLATORS:
        current_translations = translator.translate_texts(texts, language, origin_language)
        for key, values in current_translations.iteritems():
            if key not in translations:
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

if __name__ == '__main__':
    from appcomposer import app
    with app.app_context():
        print existing_translations(["Hello", "Bye", "Good morning", "This was never stored"], 'es')
        print translate_texts(["Hello", "Bye", "Good morning"], 'es')

