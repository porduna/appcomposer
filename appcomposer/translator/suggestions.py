from microsofttranslator import Translator as MSTranslator, TranslatorApiException as MSTranslatorApiException

from appcomposer.application import app
from appcomposer.db import db
from appcomposer.models import TranslationExternalSuggestion

class AbstractTranslator(object):

    def __init__(self):
        if self.name not in self.config.get('EXTERNAL_TRANSLATORS'):
            self.enabled = False
        else:
            self.enabled = True

        self.options = self.config.get('EXTERNAL_TRANSLATORS', {}).get(self.name)

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
                existing_suggestions[human_key] = value
            db.session.commit()
        return existing_suggestions

    def existing_translations(self, texts, language, origin_language = 'en'):
        """ Given a list of texts, and a language, this returns a tuple as:
        
        existing_suggestions, remaining_texts

        The first is a dictionary which maps the texts to the existing suggestions.
        The second is a dictionary which provides which texts have not been provided.
        """
        if not self.enabled:
            return {}, texts[:]

        language = language.split('_')[0]

        suggestions = db.session.query(TranslationExternalSuggestion).filter(TranslationExternalSuggestion.engine == self.name, TranslationExternalSuggestion.human_key.in_(texts), TranslationExternalSuggestion.language == language, TranslationExternalSuggestion.origin_language = origin_language).all()

        remaining_texts = texts[:]
        existing_suggestions = {}
        for suggestion in suggestions:
            existing_suggestions[suggestion.human_key] = suggestion.value
            remaining_texts.remove(suggestion.human_key)

        return existing_suggestions, remaining_texts


class MicrosoftTranslator(AbstractTranslator):
    name = 'bing'

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

        self.languages = None

    @property
    def languages(self):
        if self.languages is not None:
            return self.languages
        if self.client is None:
            self.languages = []
        self.languages = self.client.get_languages()
        return self.languages

    def _translate(self, texts, language, origin_language = 'en'):
        if self.client is None:
            return {}

        if language not in self.languages:
            return {}
        

        translations = self.translate_array(texts = texts, to_lang = language, from_lang = origin_language)
        print translations
        # TODO: what is this format?
        # TODO: what happens if the text does not exist?
        return translations


