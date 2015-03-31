import pprint
import datetime

from appcomposer import db
from appcomposer.models import TranslatedApp, TranslationUrl, TranslationBundle, ActiveTranslationMessage, TranslationMessageHistory, TranslationKeySuggestion, TranslationValueSuggestion

DEBUG = True

def add_full_translation_to_app(user, app_url, translation_url, language, target, translated_messages, original_messages):
    if DEBUG:
        print "Task:"
        print "App url:", app_url
        print "Translation URL:", translation_url
        print "Language:", language
        print "Target:", target
        print "Translated messages"
        pprint.pprint(translated_messages)
        print "Original messages"
        pprint.pprint(original_messages)

    db_translation_url = db.session.query(TranslationUrl).filter_by(url = translation_url).first()
    if not db_translation_url:
        db_translation_url = TranslationUrl(url = translation_url)
        db.session.add(db_translation_url)

    db_app_url = db.session.query(TranslatedApp).filter_by(url = app_url).first()
    if db_app_url:
        if db_app_url.translation_url is None:
            db_app_url.translation_url = db_translation_url
        elif db_app_url.translation_url != db_translation_url:
            # TODO: check whether the translation url exists
            pass
    else:
        db_app_url = TranslatedApp(url = app_url, translation_url = db_translation_url)
    db.session.add(db_app_url)

    db_translation_bundle = db.session.query(TranslationBundle).filter_by(translation_url = db_translation_url, language = language, target = target).first()
    if not db_translation_bundle:
        db_translation_bundle = TranslationBundle(language, target, db_translation_url)
        db.session.add(db_translation_bundle)
   
    unchanged = []
    parent_translation_ids = {}
    for existing_active_translation in db.session.query(ActiveTranslationMessage).filter_by(bundle = db_translation_bundle).all():
        key = existing_active_translation.key
        if key in translated_messages:
            if existing_active_translation.value != translated_messages[key]:
                parent_translation_ids[key] = existing_active_translation.history.id
                db.session.delete(existing_active_translation)
            else:
                unchanged.append(key)
    
    now = datetime.datetime.now()
    for key, value in translated_messages.iteritems():
        if key not in unchanged:
            parent_translation_id = parent_translation_ids.get(key, None)
            db_history = TranslationMessageHistory(db_translation_bundle, key, value, user, now, parent_translation_id)
            db.session.add(db_history)

            db_active_translation_message = ActiveTranslationMessage(db_translation_bundle, key, value, db_history)
            db.session.add(db_active_translation_message)

            db_existing_key_suggestion = db.session.query(TranslationKeySuggestion).filter_by(key = key, value = value, language = language, target = target).first()
            if db_existing_key_suggestion:
                db_existing_key_suggestion.number += 1
                db.session.add(db_existing_key_suggestion)
            else:
                db_key_suggestion = TranslationKeySuggestion(key = key, language = language, target = target, value = value, number = 1)
                db.session.add(db_key_suggestion)

            if key in original_messages:
                human_key = original_messages[key]

                db_existing_human_key_suggestion = db.session.query(TranslationValueSuggestion).filter_by(human_key = human_key, value = value, language = language, target = target).first()
                if db_existing_human_key_suggestion:
                    db_existing_human_key_suggestion.number += 1
                    db.session.add(db_existing_human_key_suggestion)
                else:
                    db_human_key_suggestion = TranslationValueSuggestion(human_key = human_key, language = language, target = target, value = value, number = 1)
                    db.session.add(db_human_key_suggestion)
    db.session.commit()

