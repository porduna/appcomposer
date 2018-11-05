import json
import datetime
import traceback

from celery.utils.log import get_task_logger

from appcomposer.db import db
from appcomposer.models import RepositoryApp, TranslationBundle, TranslationUrl

from appcomposer.translator.downloader import retrieve_updated_translatable_apps, retrieve_all_translatable_apps, retrieve_single_translatable_apps, update_content_hash, sync_repo_apps, download_repository_apps
from appcomposer.translator.ops import add_full_translation_to_app, retrieve_translations_percent, get_golab_default_user, start_synchronization, end_synchronization, get_bundles_by_key_namespaces

DEBUG = True
DEBUG_VERBOSE = False

logger = get_task_logger(__name__)

def _generic_synchronize_apps(source, cached, provided_apps, single_app_url, full_cycle=False):
    sync_id = start_synchronization(source = source, cached = cached, single_app_url = single_app_url)
    number = 0
    try:
        if full_cycle:
            sync_repo_apps(force=True)
            download_repository_apps()
            provided_apps = retrieve_all_translatable_apps()

        _sync_translations(provided_apps, force_reload = not cached)
        number = len(provided_apps)
    except:
        traceback.print_exc()
    finally:
        end_synchronization(sync_id, number)


def synchronize_apps_cache(source):
    """Force obtaining the results and checking everything again to avoid inconsistences. 
    This can safely be run every few minutes, since most applications will be in the cache."""
    updated_apps = retrieve_updated_translatable_apps()
    return _generic_synchronize_apps(source, cached=True, provided_apps = updated_apps, single_app_url = None)
    
def synchronize_apps_no_cache(source):
    """Force obtaining the results and checking everything again to avoid inconsistences. This should be run once a day."""
    all_apps = []
    return _generic_synchronize_apps(source, cached=True, provided_apps = all_apps, single_app_url = None, full_cycle=True)

def synchronize_single_app_no_cached(source, single_app_url):
    single_app = retrieve_single_translatable_apps(single_app_url)
    return _generic_synchronize_apps(source, cached=False, provided_apps = single_app, single_app_url = single_app_url)


def _sync_translations(apps_to_check, force_reload):
    if not apps_to_check:
        return
    
    for app_metadata in apps_to_check:

        # Make sure each request starts with a fresh database session
        db.session.remove()

        try:
            _add_or_update_app(app_url = app_metadata['app_url'], metadata_information = app_metadata['metadata'], repo_app_id=app_metadata['app_id'], force_reload=force_reload)
        except Exception as e:
            logger.warning("Error processing {}: {}".format(app_metadata['app_url'], e), exc_info=True)


def _add_or_update_app(app_url, metadata_information, repo_app_id, force_reload):
    if DEBUG:
        logger.debug("Starting %s" % app_url)

    repo_app = db.session.query(RepositoryApp).filter_by(id=repo_app_id).one()
    initial_contents_hash = repo_app.contents_hash
    initial_downloaded_hash = repo_app.downloaded_hash

    default_user = get_golab_default_user()

    translation_url = metadata_information.get('default_translation_url')
    original_messages = metadata_information['default_translations']
    default_metadata = metadata_information['default_metadata']
    for language, translated_messages in metadata_information['original_translations'].iteritems():
        add_full_translation_to_app(user_email = default_user.email, app_url = app_url, translation_url = translation_url, 
                            app_metadata = default_metadata,
                            language = language, target = u'ALL', translated_messages = translated_messages, 
                            original_messages = original_messages, from_developer = True)

    namespaces = set([ msg['namespace'] for msg in original_messages.values() if msg['namespace'] ])
    processed_languages = []
    if namespaces:
        pairs = []
        for key, msg in original_messages.iteritems():
            if msg['namespace']:
                pairs.append({
                    'key' : key,
                    'namespace' : msg['namespace'],
                })
    
        for language_pack in get_bundles_by_key_namespaces(pairs):
            cur_language = language_pack['language']
            cur_target = language_pack['target']

            if cur_target == 'ALL' and cur_language in metadata_information['original_translations']:
                # Already processed
                continue

            processed_languages.append((cur_language, cur_target))
            add_full_translation_to_app(user_email = default_user.email, app_url = app_url, translation_url = translation_url,
                            app_metadata = default_metadata,
                            language = cur_language, target = cur_target, translated_messages = {},
                            original_messages = original_messages, from_developer = False)

    db_translation_url = db.session.query(TranslationUrl).filter_by(url = translation_url).first()
    if db_translation_url:
        for translation_bundle in db.session.query(TranslationBundle).filter_by(translation_url = db_translation_url).all():
            if translation_bundle.target == u'ALL' and translation_bundle.language in metadata_information['original_translations']:
                # Already processed
                continue
            found = False
            for processed_language, processed_target in processed_languages:
                if translation_bundle.target == processed_target and translation_bundle.language == processed_language:
                    found = True
                    break

            if found:
                # Already processed
                continue

            add_full_translation_to_app(user_email = default_user.email, app_url = app_url, translation_url = translation_url, 
                        app_metadata = default_metadata,
                        language = translation_bundle.language, target = translation_bundle.target, translated_messages = None,
                        original_messages = original_messages, from_developer = False)
               

    translation_percent = retrieve_translations_percent(translation_url, original_messages)
    if translation_percent != repo_app.translation_percent:
        repo_app.translation_percent = json.dumps(translation_percent)
    
    repo_app.last_processed_contents_hash = initial_contents_hash
    repo_app.last_processed_downloaded_hash = initial_downloaded_hash
    repo_app.last_processed_time = datetime.datetime.utcnow()

    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise

    # In the meanwhile, maybe there were changes. Just make 100% sure that the hash is right
    update_content_hash(app_url)


# def _sync_regular_apps(cached_requests, synced_apps, force_reload, single_app_url = None):
#     app_urls = [ app_url for app_url, in db.session.query(TranslatedApp.url).all() ]
#     if single_app_url is not None:
#         if single_app_url in app_urls and single_app_url not in synced_apps:
#             app_urls = [ single_app_url ]
#         else:
#             return 0
# 
#     tasks_list = []
#     tasks_by_app_url = {}
#     for app_url in app_urls:
#         if app_url not in synced_apps:
#             task = MetadataTask(app_url, force_reload)
#             tasks_list.append(task)
#             tasks_by_app_url[app_url] = task
# 
#     if len(tasks_list) == 0:
#         return 0
# 
#     RunInParallel("Regular apps", tasks_list).run()
# 
#     for app_url in app_urls:
#         if app_url not in synced_apps:
#             _add_or_update_app(cached_requests, app_url, force_reload, repo_app = None, task = tasks_by_app_url[app_url])
# 
#     return len(app_urls)


if __name__ == '__main__':
    from appcomposer import create_app
    my_app = create_app()
    with my_app.app_context():
        synchronize_apps_cache()
