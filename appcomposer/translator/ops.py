import pprint
import hashlib
import datetime
from collections import defaultdict

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload_all

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
            db.session.rollback()
        except:
            db.session.rollback()
            raise
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

def get_bundles_by_key_namespaces(pairs):
    """ given a list of pairs (key, namespace), return the list of bundles which contain translations like those """
    keys = [ pair['key'] for pair in pairs ]
    namespaces = [ pair['namespace'] for pair in pairs if pair['namespace'] ]

    pairs_found = {}

    for key, namespace, bundle_id in db.session.query(ActiveTranslationMessage.key, ActiveTranslationMessage.namespace, ActiveTranslationMessage.bundle_id).filter(ActiveTranslationMessage.key.in_(keys), ActiveTranslationMessage.namespace.in_(namespaces), ActiveTranslationMessage.taken_from_default == False).all():
        pairs_found[key, namespace] = bundle_id

    bundle_ids = set()

    for pair in pairs:
        key = pair['key']
        namespace = pair['namespace']
        bundle_id = pairs_found.get((key, namespace))
        if bundle_id is not None:
            bundle_ids.add(bundle_id)
    
    bundles = []
    if bundle_ids:
        for lang, target in db.session.query(TranslationBundle.language, TranslationBundle.target).filter(TranslationBundle.id.in_(bundle_ids)).all():
            bundles.append({
                'language' : lang,
                'target' : target,
            })
    return bundles

def add_full_translation_to_app(user, app_url, translation_url, language, target, translated_messages, original_messages, from_developer):
    db_translation_bundle = _get_or_create_bundle(app_url, translation_url, language, target, from_developer)
    if from_developer and not db_translation_bundle.from_developer:
        # If this is an existing translation and it comes from a developer, establish that it is from developer
        db_translation_bundle.from_developer = from_developer

    if not from_developer and db_translation_bundle.from_developer:
        # If this is an existing translation from a developer and it comes from a user (and not a developer)
        # then it should not be accepted.
        if translated_messages is not None:
            translated_messages = translated_messages.copy()
            for msg in db_translation_bundle.active_messages:
                if msg.from_developer:
                    translated_messages.pop(msg.key, None)
            # Continue with the remaining translated_messages

    if translated_messages is not None and len(translated_messages) == 0:
        translated_messages = None

    existing_namespaces = set()
    existing_namespace_keys = set()
    existing_active_translations_with_namespace_with_default_value = []
    
    # First, update translations

    for existing_active_translation in db.session.query(ActiveTranslationMessage).filter_by(bundle = db_translation_bundle).all():
        key = existing_active_translation.key

        position = original_messages.get(key, {}).get('position')
        if position is not None and existing_active_translation.position != position:
            existing_active_translation.position = position

        category = original_messages.get(key, {}).get('category')
        if category is not None and existing_active_translation.category != category:
            existing_active_translation.category = category

        namespace = original_messages.get(key, {}).get('namespace')
        if namespace is not None and existing_active_translation.namespace != namespace:
            existing_active_translation.namespace = namespace

        if namespace is not None and existing_active_translation.taken_from_default:
            existing_namespaces.add(namespace)
            existing_namespace_keys.add(key)
            existing_active_translations_with_namespace_with_default_value.append(existing_active_translation)
    
    # Then, check namespaces

    if existing_namespaces:
        # 
        # If there are namespaces in the current bundle with words taken from default, maybe those words are already translated somewhere else.
        # So I take the existing translations for that (namespace, key, bundle), and if they exist, I use them and delete the current message
        # 
        existing_namespace_translations = {}
        _user_ids = set()

        for key, namespace, value, current_from_developer, existing_user_id in db.session.query(ActiveTranslationMessage.key, ActiveTranslationMessage.namespace, ActiveTranslationMessage.value, ActiveTranslationMessage.from_developer, TranslationMessageHistory.user_id).filter(ActiveTranslationMessage.history_id == TranslationMessageHistory.id, ActiveTranslationMessage.key.in_(list(existing_namespace_keys)), ActiveTranslationMessage.namespace.in_(list(existing_namespaces)), ActiveTranslationMessage.bundle_id == TranslationBundle.id, TranslationBundle.language == db_translation_bundle.language, TranslationBundle.target == db_translation_bundle.target, ActiveTranslationMessage.bundle_id != db_translation_bundle.id, ActiveTranslationMessage.taken_from_default == False).all():
            existing_namespace_translations[key, namespace] = (value, current_from_developer, existing_user_id)
            _user_ids.add(existing_user_id)

        existing_users = {}
        if _user_ids:
            for user in db.session.query(GoLabOAuthUser).filter(GoLabOAuthUser.id.in_(list(_user_ids))).all():
                existing_users[user.id] = user

        for wrong_message in existing_active_translations_with_namespace_with_default_value:
            now = datetime.datetime.utcnow()
            pack = existing_namespace_translations.get((wrong_message.key, wrong_message.namespace))
            if pack:
                value, current_from_developer, existing_user_id = pack
                existing_user = existing_users[existing_user_id]
                key = wrong_message.key
                wrong_history = wrong_message.history
                wrong_history_parent_id = wrong_history.id
                wrong_message_position = wrong_message.position
                wrong_message_category = wrong_message.category

                # 1st) Delete the current translation message
                db.session.delete(wrong_message)

                # 2nd) Create a new historic translation message
                new_db_history = TranslationMessageHistory(db_translation_bundle, key, value, existing_user, now, wrong_history_parent_id, False)
                db.session.add(new_db_history)

                # 3rd) Create a new active translation message
                new_db_active_translation_message = ActiveTranslationMessage(db_translation_bundle, key, value, new_db_history, now, False, wrong_message_position, wrong_message_category, current_from_developer, namespace)
                db.session.add(new_db_active_translation_message)

    if translated_messages is not None:
        # Delete active translations that are going to be replaced
        # Store which were the parents of those translations and
        # what existing translations don't need to be replaced
        unchanged = []
        parent_translation_ids = {}

        for existing_active_translation in db.session.query(ActiveTranslationMessage).filter_by(bundle = db_translation_bundle).all():
            key = existing_active_translation.key
            if key in translated_messages:
                if (translated_messages[key] and existing_active_translation.value != translated_messages[key]) or (not from_developer and existing_active_translation.taken_from_default):
                    parent_translation_ids[key] = existing_active_translation.history.id
                    db.session.delete(existing_active_translation)
                else:
                    unchanged.append(key)

        # For each translation message
        now = datetime.datetime.utcnow()
        for key, value in translated_messages.iteritems():
            if value is None:
                value = ""

            if key not in unchanged and key in original_messages:
                # Create a new history message
                parent_translation_id = parent_translation_ids.get(key, None)
                db_history = TranslationMessageHistory(db_translation_bundle, key, value, user, now, parent_translation_id, False)
                db.session.add(db_history)

                # Establish that thew new active message points to this history message
                position = original_messages[key]['position']
                category = original_messages[key]['category']
                namespace = original_messages[key]['namespace']
                db_active_translation_message = ActiveTranslationMessage(db_translation_bundle, key, value, db_history, now, False, position, category, from_developer, namespace)
                db.session.add(db_active_translation_message)

                if original_messages.get(key, {}).get('text', object()) == value:
                    # If the message in the original language is the same as in the target language, then
                    # it can be two things: 
                    # 
                    #   1) that it has been filled with the original language. In this case it should not be later displayed as a suggestion
                    #   2) that the message is the same in the original language and in the target language
                    # 
                    # Given that the original language will be a suggestion anyway, it's better to avoid storing this message as suggestion
                    continue


                if namespace:
                    # 
                    # If namespace, maybe this key is present in other translations. Therefore, I search for other translations
                    # out there in other bundles but with same language and target and the same namespace, where they are not from developer
                    # and I copy my translation to them.
                    # 
                    for wrong_message in db.session.query(ActiveTranslationMessage).filter(ActiveTranslationMessage.key == key, ActiveTranslationMessage.namespace == namespace, ActiveTranslationMessage.value != value, ActiveTranslationMessage.bundle_id == TranslationBundle.id, TranslationBundle.language == db_translation_bundle.language, TranslationBundle.target == db_translation_bundle.target, TranslationBundle.id != db_translation_bundle.id, ActiveTranslationMessage.from_developer == False).options(joinedload_all('bundle')).all():
                        # wrong_message is a message for same language, target, key and namespace with a different value.
                        # We must update it with the current credentials
                        wrong_history = wrong_message.history
                        wrong_history_parent_id = wrong_history.id
                        wrong_message_position = wrong_message.position
                        wrong_message_category = wrong_message.category
                        wrong_message_bundle = wrong_message.bundle

                        # 1st) Delete the current translation message
                        db.session.delete(wrong_message)

                        # 2nd) Create a new historic translation message
                        new_db_history = TranslationMessageHistory(wrong_message_bundle, key, value, user, now, wrong_history_parent_id, False)
                        db.session.add(new_db_history)

                        # 3rd) Create a new active translation message
                        new_db_active_translation_message = ActiveTranslationMessage(wrong_message_bundle, key, value, new_db_history, now, False, wrong_message_position, wrong_message_category, from_developer, namespace)
                        db.session.add(new_db_active_translation_message)
                
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
                    human_key = original_messages[key]['text']

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
        except:
            db.session.rollback()
            raise

    now = datetime.datetime.utcnow()
    existing_keys = [ key for key, in db.session.query(ActiveTranslationMessage.key).filter_by(bundle = db_translation_bundle).all() ]

    namespaces = [ value['namespace'] for key, value in original_messages.iteritems() if key not in existing_keys and value['namespace'] ]
    if namespaces:
        existing_namespaces = {}
        _user_ids = set()
        for key, namespace, value, current_from_developer, existing_user_id in db.session.query(ActiveTranslationMessage.key, ActiveTranslationMessage.namespace, ActiveTranslationMessage.value, ActiveTranslationMessage.from_developer, TranslationMessageHistory.user_id).filter(ActiveTranslationMessage.history_id == TranslationMessageHistory.id, ActiveTranslationMessage.key.in_(original_messages.keys()), ActiveTranslationMessage.namespace.in_(list(namespaces)), ActiveTranslationMessage.bundle_id == TranslationBundle.id, TranslationBundle.language == db_translation_bundle.language, TranslationBundle.target == db_translation_bundle.target, ActiveTranslationMessage.taken_from_default == False).all():
            existing_namespaces[key, namespace] = (value, current_from_developer, existing_user_id)
            _user_ids.add(existing_user_id)

        existing_users = {}
        if _user_ids:
            for user in db.session.query(GoLabOAuthUser).filter(GoLabOAuthUser.id.in_(list(_user_ids))).all():
                existing_users[user.id] = user
    else:
        existing_namespaces = {}
        existing_users = {}

    for key, original_message_pack in original_messages.iteritems():
        if key not in existing_keys:
            value = original_message_pack['text'] or ''
            position = original_message_pack['position']
            category = original_message_pack['category']
            namespace = original_message_pack['namespace']
            taken_from_default = True
            
            # If there is a namespace, try to get the value from other namespaces, and override the current value
            current_from_developer = False
            existing_user = user
            if namespace:
                pack = existing_namespaces.get((key, namespace), None)
                if pack is not None:
                    value, current_from_developer, existing_user_id = pack
                    existing_user = existing_users[existing_user_id]
                    taken_from_default = False

            # Create a new translation establishing that it was generated with the default value (and therefore it should be changed)
            db_history = TranslationMessageHistory(db_translation_bundle, key, value, existing_user, now, None, taken_from_default = taken_from_default)
            db.session.add(db_history)
            
            # Establish that thew new active message points to this history message
            db_active_translation_message = ActiveTranslationMessage(db_translation_bundle, key, value, db_history, now, taken_from_default = taken_from_default, position = position, category = category, from_developer = current_from_developer, namespace = namespace)
            db.session.add(db_active_translation_message)

    for existing_key in existing_keys:
        if existing_key not in original_messages:
            old_translations = db.session.query(ActiveTranslationMessage).filter_by(bundle = db_translation_bundle, key = existing_key).all()
            for old_translation in old_translations:
                db.session.delete(old_translation)

    for key, namespace in db.session.query(ActiveTranslationMessage.key, ActiveTranslationMessage.namespace).filter_by(bundle = db_translation_bundle).group_by(ActiveTranslationMessage.key, ActiveTranslationMessage.namespace).having(func.count(ActiveTranslationMessage.key) > 1).all():
        best_chance = None
        all_chances = []
        for am in db.session.query(ActiveTranslationMessage).filter_by(key = key, namespace = namespace, bundle = db_translation_bundle).all():
            all_chances.append(am)
            if best_chance is None:
                best_chance = am
            elif not am.taken_from_default and best_chance.taken_from_default:
                best_chance = am
            elif am.from_developer and not best_chance.from_developer:
                best_chance = am
        for chance in all_chances:
            if chance != best_chance:
                db.session.delete(chance)

    # Commit!
    try:
        db.session.commit()
    except IntegrityError:
        # Somebody else did this
        db.session.rollback()
    except:
        db.session.rollback()
        raise
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
    except:
        db.session.rollback()
        raise
    else:
        # Delay the synchronization process
        from appcomposer.translator.tasks import synchronize_apps_no_cache_wrapper
        synchronize_apps_no_cache_wrapper.delay()

def retrieve_stored(translation_url, language, target):
    db_translation_url = db.session.query(TranslationUrl).filter_by(url = translation_url).first()
    if db_translation_url is None:
        return {}, False, False

    bundle = db.session.query(TranslationBundle).filter_by(translation_url = db_translation_url, language = language, target = target).first()

    if bundle is None:
        return {}, False, False

    response = {}
    for message in bundle.active_messages:
        response[message.key] = {
            'value' : message.value,
            'from_default' : message.taken_from_default,
            'from_developer' : message.from_developer,
        }
    return response, bundle.from_developer, db_translation_url.automatic

SKIP_SUGGESTIONS_IF_STORED = False

def retrieve_suggestions(original_messages, language, target, stored_translations):
    original_keys = [ key for key in original_messages ]
    if SKIP_SUGGESTIONS_IF_STORED:
        original_keys = [ key for key in original_keys if key not in stored_translations ]
    original_values = [ original_messages[key]['text'] for key in original_keys ]
    original_keys_by_value = { 
        # value : [key1, key2]
    }
    for key, original_message_pack in original_messages.iteritems():
        value = original_message_pack['text']
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
                TranslationBundle.from_developer == False, 

                ActiveTranslationMessage.taken_from_default == False,

                ActiveTranslationMessage.key.in_(list(original_messages)),
                ActiveTranslationMessage.bundle_id == TranslationBundle.id, 
                TranslationBundle.translation_url_id == TranslationUrl.id, 

                TranslationUrl.url == translation_url,
            ).group_by(TranslationBundle.language, TranslationBundle.target).all()

    results_from_developers = db.session.query(func.count(ActiveTranslationMessage.key), func.max(ActiveTranslationMessage.datetime), func.min(ActiveTranslationMessage.datetime), TranslationBundle.language, TranslationBundle.target).filter(
                TranslationBundle.from_developer == True, 
                or_(ActiveTranslationMessage.from_developer == True, ActiveTranslationMessage.taken_from_default == False),

                ActiveTranslationMessage.key.in_(list(original_messages)),
                ActiveTranslationMessage.bundle_id == TranslationBundle.id, 
                TranslationBundle.translation_url_id == TranslationUrl.id, 
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

        items = len(original_messages)

        translations[lang]['targets'][target] = {
            'modification_date' : mdate,
            'creation_date' : cdate,
            'name' : GROUPS.get(target),
            'translated' : count,
            'items' : items,
        }
    
    return translations


def retrieve_translations_percent(translation_url, original_messages):
    percent = {
        # es_ES_ALL : 0.8
    }

    translations_stats = retrieve_translations_stats(translation_url, original_messages)
    for lang, lang_package in translations_stats.iteritems():
        targets = lang_package.get('targets', {})
        for target, target_stats in targets.iteritems():
            translated = target_stats['translated']
            total_items = target_stats['items']
            percent['%s_%s' % (lang, target)] = 1.0 * translated / total_items

    return percent

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
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise
        db.session.refresh(t_history)
        src_message_ids[msg.id] = t_history.id
        historic[msg.id] = t_history

    now = datetime.datetime.utcnow()
    for msg in src_bundle.active_messages:
        history = historic.get(msg.history_id)
        active_t = ActiveTranslationMessage(dst_bundle, msg.key, msg.value, history, now, msg.taken_from_default, msg.position, msg.category, msg.from_developer, msg.namespace)
        db.session.add(active_t)

    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise

def _merge_bundle(src_bundle, dst_bundle):
    """Copy all the messages. The destination bundle already existed, so we can only copy those
    messages not present."""
    now = datetime.datetime.utcnow()
    for msg in src_bundle.active_messages:
        existing_translation = db.session.query(ActiveTranslationMessage).filter_by(bundle = dst_bundle, key = msg.key).first()
        if existing_translation is None:
            t_history = TranslationMessageHistory(dst_bundle, msg.key, msg.value, msg.history.user, now, None, msg.taken_from_default)
            db.session.add(t_history)
            active_t = ActiveTranslationMessage(dst_bundle, msg.key, msg.value, t_history, now, msg.taken_from_default, msg.position, msg.category, msg.from_developer, msg.namespace)
            db.session.add(active_t)
            try:
                db.session.commit()
            except:
                db.session.rollback()
                raise
        elif existing_translation.taken_from_default and not msg.taken_from_default:
            # Merge it
            t_history = TranslationMessageHistory(dst_bundle, msg.key, msg.value, msg.history.user, now, existing_translation.history.id, msg.taken_from_default)
            db.session.add(t_history)
            active_t = ActiveTranslationMessage(dst_bundle, msg.key, msg.value, t_history, now, msg.taken_from_default, msg.position, msg.category, msg.from_developer, msg.namespace)
            db.session.add(active_t)
            db.session.delete(existing_translation)
            try:
                db.session.commit()
            except:
                db.session.rollback()
                raise

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
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise
    db.session.refresh(sync_log)
    print "Starting synchronization %s" % sync_log.id
    return sync_log.id

def end_synchronization(sync_id):
    now = datetime.datetime.utcnow()
    sync_log = db.session.query(TranslationSyncLog).filter_by(id = sync_id).first()
    if sync_log is not None:
        sync_log.end_datetime = now
        print "Synchronization %s finished" % sync_log.id
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise

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
    
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise

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

