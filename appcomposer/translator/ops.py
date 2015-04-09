import pprint
import datetime

from appcomposer import db
from appcomposer.models import TranslatedApp, TranslationUrl, TranslationBundle, ActiveTranslationMessage, TranslationMessageHistory, TranslationKeySuggestion, TranslationValueSuggestion

DEBUG = False

def add_full_translation_to_app(user, app_url, translation_url, language, target, translated_messages, original_messages, from_developer):
    if DEBUG:
        print "Task:"
        print "App url:", app_url
        print "Translation URL:", translation_url
        print "Language:", language
        print "Target:", target
        print "From developer:", from_developer
        print "Translated messages"
        pprint.pprint(translated_messages)
        print "Original messages"
        pprint.pprint(original_messages)
    
    # Create the translation url if not present
    db_translation_url = db.session.query(TranslationUrl).filter_by(url = translation_url).first()
    if not db_translation_url:
        db_translation_url = TranslationUrl(url = translation_url)
        db.session.add(db_translation_url)

    # Create the app if not present
    db_app_url = db.session.query(TranslatedApp).filter_by(url = app_url).first()
    if db_app_url:
        if db_app_url.translation_url is None:
            db_app_url.translation_url = db_translation_url
        elif db_app_url.translation_url != db_translation_url:
            # If present with a different translation url, copy the old one if possible
            _deep_copy_translations(db_app_url.translation_url, db_translation_url, dont_commit = True)
            db_app_url.translation_url = db_translation_url
    else:
        db_app_url = TranslatedApp(url = app_url, translation_url = db_translation_url)
    db.session.add(db_app_url)

    # Create the bundle if not present
    db_translation_bundle = db.session.query(TranslationBundle).filter_by(translation_url = db_translation_url, language = language, target = target).first()
    if not db_translation_bundle:
        db_translation_bundle = TranslationBundle(language, target, db_translation_url, from_developer)
        db.session.add(db_translation_bundle)
   
    if translated_messages is not None:
        # Delete active translations that are going to be replaced
        # Store which were the parents of those translations and
        # what existing translations don't need to be replaced
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
        
        # For each translation message
        now = datetime.datetime.now()
        for key, value in translated_messages.iteritems():
            if key not in unchanged:
                # Create a new history message
                parent_translation_id = parent_translation_ids.get(key, None)
                db_history = TranslationMessageHistory(db_translation_bundle, key, value, user, now, parent_translation_id)
                db.session.add(db_history)

                # Establish that thew new active message points to this history message
                db_active_translation_message = ActiveTranslationMessage(db_translation_bundle, key, value, db_history)
                db.session.add(db_active_translation_message)

                # Create a suggestion based on the key
                db_existing_key_suggestion = db.session.query(TranslationKeySuggestion).filter_by(key = key, value = value, language = language, target = target).first()
                if db_existing_key_suggestion:
                    db_existing_key_suggestion.number += 1
                    db.session.add(db_existing_key_suggestion)
                else:
                    db_key_suggestion = TranslationKeySuggestion(key = key, language = language, target = target, value = value, number = 1)
                    db.session.add(db_key_suggestion)

                # Create a suggestion based on the value
                if original_messages is not None and key in original_messages:
                    human_key = original_messages[key]

                    db_existing_human_key_suggestion = db.session.query(TranslationValueSuggestion).filter_by(human_key = human_key, value = value, language = language, target = target).first()
                    if db_existing_human_key_suggestion:
                        db_existing_human_key_suggestion.number += 1
                        db.session.add(db_existing_human_key_suggestion)
                    else:
                        db_human_key_suggestion = TranslationValueSuggestion(human_key = human_key, language = language, target = target, value = value, number = 1)
                        db.session.add(db_human_key_suggestion)

    # Commit!
    db.session.commit()

def retrieve_stored(translation_url, language, target):
    db_translation_url = db.session.query(TranslationUrl).filter_by(url = translation_url).first()
    if db_translation_url is None:
        return {}

    bundle = db.session.query(TranslationBundle).filter_by(translation_url = db_translation_url, language = language, target = target).first()

    if bundle is None:
        return {}

    response = {}
    for message in bundle.active_messages:
        response[message.key] = message.value
    return response

SKIP_SUGGESTIONS_IF_STORED = False

def retrieve_suggestions(original_messages, language, target, stored_translations):
    all_suggestions = {}

    # TODO: move these to two single queries, calculating the order manually
    # and adding the values of the potential values

    # First, based on key:
    for key in original_messages:
        if SKIP_SUGGESTIONS_IF_STORED and key in stored_translations:
            continue

        all_suggestions[key] = []

        for key_suggestion in db.session.query(TranslationKeySuggestion).filter_by(key = key, language = language, target = target).order_by(TranslationKeySuggestion.number.desc()).all():
            value = key_suggestion.value
            if value not in all_suggestions[key]:
                all_suggestions[key].append(value)

    # Then, based on the value:
    for key, original_value in original_messages.iteritems():
        if SKIP_SUGGESTIONS_IF_STORED and key in stored_translations:
            continue
        
        for value_suggestion in db.session.query(TranslationValueSuggestion).filter_by(human_key = original_value, language = language, target = target).order_by(TranslationValueSuggestion.number.desc()).all():
            value = value_suggestion.value
            if value not in all_suggestions[key]:
                all_suggestions[key].append(value)

    # TODO: here is where we could put the Bing / whatever values if there is nothing already

    return all_suggestions

def _deep_copy_bundle(src_bundle, dst_bundle):
    """Copy all the messages. Safely assume that there is no translation in the destination, so
    we can copy all the history, active, etc.
    """
    pass # TODO

def _merge_bundle(src_bundle, dst_bundle):
    """Copy all the messages. The destination bundle already existed, so we can only copy those
    messages not present."""
    pass # TODO

def _deep_copy_translations(old_translation_url, new_translation_url):
    """Given an old translation of a URL, take the old bundles and copy them to the new one."""
    new_bundles = {}
    for new_bundle in new_translation_url.bundles:
        new_bundle[new_bundle.language, new_bundle.target] = new_bundle

    for old_bundle in old_translation_url.bundles:
        new_bundle = new_bundles.get((old_bundle.language, old_bundle.target))
        if new_bundle:
            _merge_bundle(old_bundle, new_bundle)
        else:
            new_bundle = TranslationBundle(old_bundle.language, old_bundle.target, new_translation_url)
            db.session.add(new_bundle)
            _deep_copy_bundle(old_bundle, new_bundle)

