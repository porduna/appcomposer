import pprint
import datetime
from collections import defaultdict

from sqlalchemy import func

from appcomposer import db
from appcomposer.models import TranslatedApp, TranslationUrl, TranslationBundle, ActiveTranslationMessage, TranslationMessageHistory, TranslationKeySuggestion, TranslationValueSuggestion

DEBUG = False

def add_full_translation_to_app(user, app_url, translation_url, language, target, translated_messages, original_messages, from_developer):
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
            _deep_copy_translations(db_app_url.translation_url, db_translation_url)
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
                db_history = TranslationMessageHistory(db_translation_bundle, key, value, user, now, parent_translation_id, False)
                db.session.add(db_history)

                # Establish that thew new active message points to this history message
                db_active_translation_message = ActiveTranslationMessage(db_translation_bundle, key, value, db_history, now, False)
                db.session.add(db_active_translation_message)
                
                if original_messages[key] == value:
                    # If the message in the original language is the same as in the target language, then
                    # it can be two things: 
                    # 
                    #   1) that it has been filled with the original language. In this case it should not be later displayed as a suggestion
                    #   2) that the message is the same in the original language and in the target language
                    # 
                    # Given that the original language will be a suggestion anyway, it's better to avoid storing this message as suggestion
                    continue

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
        db.session.commit()

    existing_keys = [ key for key, in db.session.query(ActiveTranslationMessage.key).filter_by(bundle = db_translation_bundle).all() ]
    for key, value in original_messages.iteritems():
        if key not in existing_keys:
            # Create a new translation establishing that it was generated with the default value (and therefore it should be changed)
            db_history = TranslationMessageHistory(db_translation_bundle, key, value, user, now, None, True)
            db.session.add(db_history)

            # Establish that thew new active message points to this history message
            db_active_translation_message = ActiveTranslationMessage(db_translation_bundle, key, value, db_history, now, True)
            db.session.add(db_active_translation_message)

    # Commit!
    db.session.commit()

def retrieve_stored(translation_url, language, target):
    db_translation_url = db.session.query(TranslationUrl).filter_by(url = translation_url).first()
    if db_translation_url is None:
        return {}, False

    bundle = db.session.query(TranslationBundle).filter_by(translation_url = db_translation_url, language = language, target = target).first()

    if bundle is None:
        return {}, False

    response = {}
    for message in bundle.active_messages:
        response[message.key] = {
            'value' : message.value,
            'from_default' : message.taken_from_default,
        }
    return response, bundle.from_developer

SKIP_SUGGESTIONS_IF_STORED = False

def retrieve_suggestions(original_messages, language, target, stored_translations):
    original_keys = [ key for key in original_messages ]
    if SKIP_SUGGESTIONS_IF_STORED:
        original_keys = [ key for key in original_keys if key not in stored_translations ]
    original_values = [ original_messages[key] for key in original_keys ]

    all_suggestions = {}
    current_suggestions = []

    # First, key suggestions
    key_suggestions_by_key = defaultdict(list)
    for key_suggestion in db.session.query(TranslationKeySuggestion).filter_by(language = language, target = target).filter(TranslationKeySuggestion.key.in_(original_keys)).all():
        key_suggestions_by_key[key_suggestion.key].append({
            'target' : key_suggestion.value,
            'number' : key_suggestion.number,
        })
    current_suggestions.append(key_suggestions_by_key)

    # Second, value suggestions
    value_suggestions_by_key = defaultdict(list)
    for value_suggestion in db.session.query(TranslationValueSuggestion).filter_by(language = language, target = target).filter(TranslationValueSuggestion.human_key.in_(original_values)).all():
        value_suggestions_by_key[value_suggestion.human_key].append({
            'target' : value_suggestion.value,
            'number' : value_suggestion.number,
        })
    current_suggestions.append(value_suggestions_by_key)

    # TODO: here is where we could put the Bing / whatever values if there is nothing already

    for key in original_keys:
        current_key_suggestions = defaultdict(int)
        # { 'target' : number }

        for suggestions in current_suggestions:
            for suggestion in suggestions.get(key, []):
                current_key_suggestions[suggestion['target']] += suggestion['number']

        all_suggestions[key] = []
        if current_key_suggestions:
            # Normalize the maximum value
            total_value = max(current_key_suggestions.values())
            for target, number in current_key_suggestions.iteritems():
                normalized_value = 1.0 * number / total_value
                all_suggestions[key].append({
                    'target' : target,
                    'weight' : normalized_value,
                })
            all_suggestions[key].sort(lambda x1, x2: cmp(x1['weight'], x2['weight']), reverse = True)

    return all_suggestions

def retrieve_translations_percent(translation_url, original_messages):
    if len(original_messages) == 0:
        return {}

    results = db.session.query(func.count(ActiveTranslationMessage.key), TranslationBundle.language, TranslationBundle.target).filter(
                ActiveTranslationMessage.key.in_(list(original_messages)),
                ActiveTranslationMessage.taken_from_default == False,
                ActiveTranslationMessage.bundle_id == TranslationBundle.id, 
                TranslationBundle.translation_url_id == TranslationUrl.id, 
                TranslationUrl.url == translation_url,
            ).group_by(TranslationBundle.language, TranslationBundle.target).all()

    translations = {
        # es_ES_ALL : 0.8
    }

    for count, lang, target in results:
        bundle = u'%s_%s' % (lang, target)
        translations[bundle] = 1.0 * count / len(original_messages)

    return translations

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

