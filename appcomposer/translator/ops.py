import pprint
import hashlib
import datetime
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from appcomposer import db
from appcomposer.application import app
from appcomposer.translator.languages import obtain_languages, obtain_groups
from appcomposer.translator.suggestions import translate_texts
from appcomposer.models import TranslatedApp, TranslationUrl, TranslationBundle, ActiveTranslationMessage, TranslationMessageHistory, TranslationKeySuggestion, TranslationValueSuggestion, GoLabOAuthUser, TranslationSyncLog, TranslationCurrentActiveUser

DEBUG = False

LANGUAGES = obtain_languages()
GROUPS = obtain_groups()

def get_golab_default_user():
    default_email = app.config.get('TRANSLATOR_DEFAULT_EMAIL', 'weblab+appcomposer@deusto.es')
    default_user = db.session.query(GoLabOAuthUser).filter_by(email = default_email).first()
    if default_user is None:
        default_user = GoLabOAuthUser(email = default_email, display_name = "AppComposer")
        db.session.add(default_user)
        try:
            db.session.commit()
        except IntegrityError:
            default_user = db.session.query(GoLabOAuthUser).filter_by(email = default_email).first()
    return default_user

def _get_or_create_app(app_url, translation_url):
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
    return db_translation_url

def _get_or_create_bundle(app_url, translation_url, language, target, from_developer):
    db_translation_url = _get_or_create_app(app_url, translation_url)

    # Create the bundle if not present
    db_translation_bundle = db.session.query(TranslationBundle).filter_by(translation_url = db_translation_url, language = language, target = target).first()
    if not db_translation_bundle:
        db_translation_bundle = TranslationBundle(language, target, db_translation_url, from_developer)
        db.session.add(db_translation_bundle)
    return db_translation_bundle

def add_full_translation_to_app(user, app_url, translation_url, language, target, translated_messages, original_messages, from_developer):
    db_translation_bundle = _get_or_create_bundle(app_url, translation_url, language, target, from_developer)
    if from_developer and not db_translation_bundle.from_developer:
        # If this is an existing translation and it comes from a developer, establish that it is from developer
        db_translation_bundle.from_developer = from_developer

    if not from_developer and db_translation_bundle.from_developer:
        # If this is an existing translation from a developer and it comes from a user (and not a developer)
        # then it should not be accepted.
        return
        
   
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
        now = datetime.datetime.utcnow()
        for key, value in translated_messages.iteritems():
            if key not in unchanged:
                # Create a new history message
                parent_translation_id = parent_translation_ids.get(key, None)
                db_history = TranslationMessageHistory(db_translation_bundle, key, value, user, now, parent_translation_id, False)
                db.session.add(db_history)

                # Establish that thew new active message points to this history message
                db_active_translation_message = ActiveTranslationMessage(db_translation_bundle, key, value, db_history, now, False)
                db.session.add(db_active_translation_message)
                
                if original_messages.get(key, object()) == value:
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
        try:
            db.session.commit()
        except IntegrityError:
            # Somebody else concurrently run this
            db.session.rollback() 

    now = datetime.datetime.utcnow()
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
    try:
        db.session.commit()
    except IntegrityError:
        # Somebody else did this
        db.session.rollback()
    else:
        from appcomposer.translator.tasks import push_task
        push_task.delay(translation_url, language, target)
    
def register_app_url(app_url, translation_url):
    _get_or_create_app(app_url, translation_url)
    try:
        db.session.commit()
    except IntegrityError:
        # Somebody else did this process
        db.session.rollback()
    else:
        # Delay the synchronization process
        from appcomposer.translator.tasks import synchronize_apps_no_cache_wrapper
        synchronize_apps_no_cache_wrapper.delay()

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
    original_keys_by_value = { 
        # value : [key1, key2]
    }
    for key, value in original_messages.iteritems():
        if value not in original_keys_by_value:
            original_keys_by_value[value] = []
        original_keys_by_value[value].append(key)

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
        for key in original_keys_by_value.get(value_suggestion.human_key, []):
            value_suggestions_by_key[key].append({
                'target' : value_suggestion.value,
                'number' : value_suggestion.number,
            })

    for human_key, suggested_values in translate_texts(original_values, language).iteritems():
        for key in original_keys_by_value.get(human_key, []):
            for suggested_value, weight in suggested_values.iteritems():
                value_suggestions_by_key[key].append({
                    'target' : suggested_value,
                    'number' : weight,
                })

    current_suggestions.append(value_suggestions_by_key)

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

def retrieve_translations_stats(translation_url, original_messages):
    if len(original_messages) == 0:
        return {}
    
    results_from_users = db.session.query(func.count(ActiveTranslationMessage.key), func.max(ActiveTranslationMessage.datetime), func.min(ActiveTranslationMessage.datetime), TranslationBundle.language, TranslationBundle.target).filter(
                ActiveTranslationMessage.key.in_(list(original_messages)),
                ActiveTranslationMessage.taken_from_default == False,
                ActiveTranslationMessage.bundle_id == TranslationBundle.id, 
                TranslationBundle.translation_url_id == TranslationUrl.id, 
                TranslationBundle.from_developer == False, 
                TranslationUrl.url == translation_url,
            ).group_by(TranslationBundle.language, TranslationBundle.target).all()

    results_from_developers = db.session.query(func.count(ActiveTranslationMessage.key), func.max(ActiveTranslationMessage.datetime), func.min(ActiveTranslationMessage.datetime), TranslationBundle.language, TranslationBundle.target).filter(
                ActiveTranslationMessage.key.in_(list(original_messages)),
                ActiveTranslationMessage.bundle_id == TranslationBundle.id, 
                TranslationBundle.translation_url_id == TranslationUrl.id, 
                TranslationBundle.from_developer == True, 
                TranslationUrl.url == translation_url,
            ).group_by(TranslationBundle.language, TranslationBundle.target).all()

    results = results_from_users
    results.extend(results_from_developers)

    translations = {
        # es_ES : {
        #      "name" : foo,
        #      "targets" : {
        #           "ALL" : {
        #                "modified_date" : "2014-02-14",
        #                "creation_date" : "2014-02-14",
        #                "name" : "Adolescens...,
        #                "translated" : 21,
        #                "items" : 31,
        #           }
        #      }
        # }
    }

    for count, modification_date, creation_date, lang, target in results:
        if lang not in translations:
            translations[lang] = {
                'name' : LANGUAGES.get(lang),
                'targets' : {}
            }

        mdate = modification_date.strftime("%Y-%m-%d") if modification_date is not None else None
        cdate = creation_date.strftime("%Y-%m-%d") if creation_date is not None else None

        translations[lang]['targets'][target] = {
            'modification_date' : mdate,
            'creation_date' : cdate,
            'name' : GROUPS.get(target),
            'translated' : count,
            'items' : len(original_messages)
        }
    
    return translations


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
    src_message_ids = {
        # old_id : new_id
    }
    historic = {
        # old_id : new historic instance
    }
    for msg in src_bundle.all_messages:
        t_history = TranslationMessageHistory(dst_bundle, msg.key, msg.value, msg.user, msg.datetime, src_message_ids.get(msg.parent_translation_id), msg.taken_from_default)
        db.session.add(t_history)
        db.session.commit()
        db.session.refresh(t_history)
        src_message_ids[msg.id] = t_history.id
        historic[msg.id] = t_history

    now = datetime.datetime.utcnow()
    for msg in src_bundle.active_messages:
        history = historic.get(msg.history_id)
        active_t = ActiveTranslationMessage(dst_bundle, msg.key, msg.value, history, now, msg.taken_from_default)
        db.session.add(active_t)

    db.session.commit()

def _merge_bundle(src_bundle, dst_bundle):
    """Copy all the messages. The destination bundle already existed, so we can only copy those
    messages not present."""
    now = datetime.datetime.utcnow()
    for msg in src_bundle.active_messages:
        existing_translation = db.session.query(ActiveTranslationMessage).filter_by(bundle = dst_bundle, key = msg.key).first()
        if existing_translation is None:
            t_history = TranslationMessageHistory(dst_bundle, msg.key, msg.value, msg.history.user, now, None, msg.taken_from_default)
            db.session.add(t_history)
            active_t = ActiveTranslationMessage(dst_bundle, msg.key, msg.value, t_history, now, msg.taken_from_default)
            db.session.add(active_t)
            db.session.commit()
        elif existing_translation.taken_from_default and not msg.taken_from_default:
            # Merge it
            t_history = TranslationMessageHistory(dst_bundle, msg.key, msg.value, msg.history.user, now, existing_translation.history.id, msg.taken_from_default)
            db.session.add(t_history)
            active_t = ActiveTranslationMessage(dst_bundle, msg.key, msg.value, t_history, now, msg.taken_from_default)
            db.session.add(active_t)
            db.session.delete(existing_translation)
            db.session.commit()

def _deep_copy_translations(old_translation_url, new_translation_url):
    """Given an old translation of a URL, take the old bundles and copy them to the new one."""
    new_bundles = {}
    for new_bundle in new_translation_url.bundles:
        new_bundles[new_bundle.language, new_bundle.target] = new_bundle

    for old_bundle in old_translation_url.bundles:
        new_bundle = new_bundles.get((old_bundle.language, old_bundle.target))
        if new_bundle:
            _merge_bundle(old_bundle, new_bundle)
        else:
            new_bundle = TranslationBundle(old_bundle.language, old_bundle.target, new_translation_url, old_bundle.from_developer)
            db.session.add(new_bundle)
            _deep_copy_bundle(old_bundle, new_bundle)

def start_synchronization():
    now = datetime.datetime.utcnow()
    sync_log = TranslationSyncLog(now, None)
    db.session.add(sync_log)
    db.session.commit()
    db.session.refresh(sync_log)
    return sync_log.id

def end_synchronization(sync_id):
    now = datetime.datetime.utcnow()
    sync_log = db.session.query(TranslationSyncLog).filter_by(id = sync_id).first()
    if sync_log is not None:
        sync_log.end_datetime = now
        db.session.commit()

def get_latest_synchronizations():
    latest_syncs = db.session.query(TranslationSyncLog)[-10:]
    return [
        {
            'id' : sync.id,
            'start' : sync.start_datetime,
            'end' : sync.end_datetime
        } for sync in latest_syncs
    ]

def update_user_status(language, target, app_url, user):
    translated_app = db.session.query(TranslatedApp).filter_by(url = app_url).first()
    if translated_app is None:
        return
    
    translation_url = translated_app.translation_url
    if translation_url is None:
        return

    bundle = db.session.query(TranslationBundle).filter_by(translation_url = translation_url, language = language, target = target).first()
    if bundle is None:
        return

    if user is None:
        print "ERROR: user can't be NULL"
        return

    active_user = db.session.query(TranslationCurrentActiveUser).filter_by(bundle = bundle, user = user).first()
    if active_user is None:
        active_user = TranslationCurrentActiveUser(user = user, bundle = bundle)
        db.session.add(active_user)
    else:
        active_user.update_last_check()

    db.session.commit()

def get_user_status(language, target, app_url, user):
    FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    now = datetime.datetime.utcnow()
    now_str = now.strftime(FORMAT)

    ERROR = {
        'modificationDate': now_str,
        'modificationDateByOther': now_str,
        'time_now': now_str,
        'collaborators': []
    }
    translated_app = db.session.query(TranslatedApp).filter_by(url = app_url).first()
    if translated_app is None:
        ERROR['error_msg'] = "Translation App URL not found"
        return ERROR
    
    translation_url = translated_app.translation_url
    if translation_url is None:
        ERROR['error_msg'] = "Translation Translation URL not found"
        return ERROR

    bundle = db.session.query(TranslationBundle).filter_by(translation_url = translation_url, language = language, target = target).first()
    if bundle is None:
        ERROR['error_msg'] = "Bundle not found"
        return ERROR

    last_change_by_user = db.session.query(func.max(ActiveTranslationMessage.datetime), TranslationMessageHistory.user_id).filter(ActiveTranslationMessage.history_id == TranslationMessageHistory.id, ActiveTranslationMessage.bundle == bundle).group_by(TranslationMessageHistory.user_id).all()

    modification_date = None
    modification_date_by_other = None
    for last_change, user_id in last_change_by_user:
        if user_id == user.id:
            modification_date = last_change
        else:
            if modification_date_by_other is None or modification_date_by_other < last_change:
                modification_date_by_other = last_change

    if modification_date is None and modification_date_by_other is not None:
        modification_date = modification_date_by_other

    # Find collaborators (if any)
    latest_minutes = now - datetime.timedelta(minutes = 1)
    db_collaborators = db.session.query(TranslationCurrentActiveUser).filter(TranslationCurrentActiveUser.bundle == bundle, TranslationCurrentActiveUser.last_check > latest_minutes).all()
    collaborators = []
    for collaborator in db_collaborators:
        if collaborator.user != user and collaborator.user is not None:
            collaborators.append({
                'name' : collaborator.user.display_name,
                'md5' : hashlib.md5(collaborator.user.email).hexdigest(),
            })
    
    return {
        'modificationDate': modification_date.strftime(FORMAT) if modification_date is not None else None,
        'modificationDateByOther': modification_date_by_other.strftime(FORMAT) if modification_date_by_other is not None else None,
        'time_now': now_str,
        'collaborators': collaborators
    }

