import sys
import time
import json
import datetime
import threading

import goslate
import requests

from flask import url_for
from sqlalchemy.exc import SQLAlchemyError
from celery.utils.log import get_task_logger

from appcomposer.application import app
from appcomposer.db import db
from appcomposer.models import RepositoryApp, TranslatedApp, ActiveTranslationMessage, TranslationBundle, TranslationUrl, TranslationExternalSuggestion

from appcomposer.translator.languages import SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES, OFFICIAL_EUROPEAN_UNION_LANGUAGES, OTHER_LANGUAGES
from appcomposer.translator.utils import extract_metadata_information
import appcomposer.translator.utils as trutils
from appcomposer.translator.ops import add_full_translation_to_app, retrieve_translations_percent, get_golab_default_user, start_synchronization, end_synchronization, get_bundles_by_key_namespaces

GOLAB_REPO = u'golabz'
EXTERNAL_REPO = u'external'

GRAASP = {
    'title': 'Graasp',
    'id': '-1',
    'description': "Graasp is the ILS platform",
    'app_url': "http://composer.golabz.eu/graasp_i18n/",
    'app_type': "OpenSocial gadget",
    'app_image': "http://composer.golabz.eu/static/img/graasp-logo.png",
    'app_thumb': "http://composer.golabz.eu/static/img/graasp-logo-thumb.png",
    'app_golabz_page': "http://graasp.eu/",
}
OTHER_APPS = app.config.get('OTHER_APPS', [ GRAASP ])

DEBUG = True

logger = get_task_logger(__name__)

def synchronize_apps_cache(single_app_url = None):
    """Force obtaining the results and checking everything again to avoid inconsistences. 
    This can safely be run every few minutes, since most applications will be in the cache."""
    sync_id = start_synchronization()
    try:
        cached_requests = trutils.get_cached_session()
        synced_apps = _sync_golab_translations(cached_requests, force_reload = False, single_app_url = single_app_url)
        _sync_regular_apps(cached_requests, synced_apps, force_reload = False, single_app_url = single_app_url)
    finally:
        end_synchronization(sync_id)
    
def synchronize_apps_no_cache(single_app_url = None):
    """Force obtaining the results and checking everything again to avoid inconsistences. This should be run once a day."""
    sync_id = start_synchronization()
    try:
        cached_requests = trutils.get_cached_session()
        synced_apps = _sync_golab_translations(cached_requests, force_reload = True, single_app_url = single_app_url)
        _sync_regular_apps(cached_requests, synced_apps, force_reload = True, single_app_url = single_app_url)
    finally:
        end_synchronization(sync_id)

class MetadataTask(threading.Thread):
    def __init__(self, app_url, force_reload):
        threading.Thread.__init__(self)
        self.cached_requests = trutils.get_cached_session()
        self.app_url = app_url
        self.force_reload = force_reload
        self.finished = False
        self.failing = False
        self.metadata_information = None

    def run(self):
        self.failing = False
        try:
            self.metadata_information = extract_metadata_information(self.app_url, self.cached_requests, self.force_reload)
        except Exception:
            logger.warning("Error extracting information from %s" % self.app_url, exc_info = True)
            self.metadata_information = {}
            self.failing = True
        self.finished = True

class RunInParallel(object):
    def __init__(self, tasks, thread_number = 15):
        self.tasks = tasks
        self.thread_number = thread_number

    def all_finished(self):
        for task in self.tasks:
            if not task.finished:
                return False
        return True

    def run(self):
        counter = 0
        waiting_tasks = self.tasks[:]
        running_tasks = []
        while not self.all_finished():
            has_changed = True
            while has_changed:
                has_changed = False
                cur_pos = -1
                for pos, task in enumerate(running_tasks):
                    if task.finished:
                        cur_pos = pos
                        has_changed = True
                        break
                if has_changed:
                    running_tasks.pop(cur_pos)

            while len(running_tasks) < self.thread_number and len(waiting_tasks) > 0:
                new_task = waiting_tasks.pop(0)
                new_task.start()
                running_tasks.append(new_task)

            if len(running_tasks) > 0:
                time.sleep(0.1)

        for task in self.tasks:
            task.join()

        print "All apps downloaded"

def _sync_golab_translations(cached_requests, force_reload, single_app_url = None):
    try:
        apps_response = cached_requests.get("http://www.golabz.eu/rest/apps/retrieve.json")
        apps_response.raise_for_status()
        apps = apps_response.json()
    except requests.RequestException:
        logger.warning("Error retrieving applications from golabz", exc_info = True)
        return []

    try:
        labs_response = cached_requests.get("http://www.golabz.eu/rest/labs/retrieve.json")
        labs_response.raise_for_status()
        labs = labs_response.json()
    except requests.RequestException:
        logger.warning("Error retrieving laboratories from golabz", exc_info = True)
        return []

    labs_adapted = []
    for lab in labs:
        current_lab = lab.copy()
        lab_id = lab['id']
        current_lab['app_image'] = current_lab.get('lab_image')
        current_lab['app_thumb'] = current_lab.get('lab_thumb')
        current_lab['app_golabz_page'] = current_lab.get('lab_golabz_page')
        for pos, internal_lab in enumerate(lab.get('lab_apps', [])):
            current_lab = current_lab.copy()
            current_lab['id'] = '%s-%s' % (lab_id, pos)
            current_lab['app_url'] = internal_lab['app_url']
            current_lab['app_title'] = internal_lab['app_title']
            current_lab['app_type'] = internal_lab['app_type']
            labs_adapted.append(current_lab)

    apps.extend(labs_adapted)

    apps_by_url = {}
    for app in apps:
        apps_by_url[app['app_url']] = app

    apps_by_id = {}
    for app in apps:
        apps_by_id[unicode(app['id'])] = app

    stored_apps = db.session.query(RepositoryApp).filter_by(repository=GOLAB_REPO).all()

    tasks_list = []
    tasks_by_app_url = {}
    for app_url in apps_by_url:
        if single_app_url is not None and app_url != single_app_url:
            continue
        task = MetadataTask(app_url, force_reload)
        tasks_list.append(task)
        tasks_by_app_url[app_url] = task
        

    run_in_parallel = RunInParallel(tasks_list)
    run_in_parallel.run()

    # 
    # Update or delete existing apps
    # 
    stored_ids = []
    for repo_app in stored_apps:
        external_id = unicode(repo_app.external_id)
        try:
            if external_id not in apps_by_id:
                if single_app_url is not None:
                    # In the single_app_url, do not do these things
                    continue

                # Delete old apps (translations are kept, and the app is kept, but not listed in the repository apps)
                db.session.delete(repo_app)
                try:
                    db.session.commit()
                except:
                    db.session.rollback()
                    raise
            else:
                if single_app_url is not None and single_app_url != app['app_url']:
                    continue
                stored_ids.append(unicode(external_id))
                app = apps_by_id[external_id]
                _update_existing_app(cached_requests, repo_app, app_url = app['app_url'], title = app['title'], app_thumb = app['app_thumb'], description = app['description'], app_image = app['app_image'], app_link = app['app_golabz_page'], force_reload = force_reload, task = tasks_by_app_url.get(app['app_url']))
        except SQLAlchemyError:
            # One error in one application shouldn't stop the process
            logger.warning("Error updating or deleting app %s" % app['app_url'], exc_info = True)
            continue

    #
    # Add new apps
    #
    for app in apps:
        if single_app_url is not None and single_app_url != app['app_url']:
            continue

        if unicode(app['id']) not in stored_ids:
            try:
                # Double-check
                repo_app = db.session.query(RepositoryApp).filter_by(repository = GOLAB_REPO, external_id = app['id']).first()
                if repo_app is None:
                    _add_new_app(cached_requests, repository = GOLAB_REPO, 
                                app_url = app['app_url'], title = app['title'], external_id = app['id'],
                                app_thumb = app['app_thumb'], description = app['description'],
                                app_image = app['app_image'], app_link = app['app_golabz_page'],
                                force_reload = force_reload, task = tasks_by_app_url.get(app['app_url']))
            except SQLAlchemyError:
                logger.warning("Error adding app %s" % app['app_url'], exc_info = True)
                continue

    return list(apps_by_url)

def _update_existing_app(cached_requests, repo_app, app_url, title, app_thumb, description, app_image, app_link, force_reload, task):
    if repo_app.name != title:
        repo_app.name = title
    if repo_app.app_thumb != app_thumb:
        repo_app.app_thumb = app_thumb
    if repo_app.description != description:
        repo_app.description = description
    if repo_app.app_link != app_link:
        repo_app.app_link = app_link
    if repo_app.app_image != app_image:
        repo_app.app_image = app_image

    _add_or_update_app(cached_requests, app_url, force_reload, repo_app, task)

def _add_new_app(cached_requests, repository, app_url, title, external_id, app_thumb, description, app_image, app_link, force_reload, task):
    repo_app = RepositoryApp(name = title, url = app_url, external_id = external_id, repository = repository)
    repo_app.app_thumb = app_thumb
    repo_app.description = description
    repo_app.app_link = app_link
    repo_app.app_image = app_image
    db.session.add(repo_app)

    _add_or_update_app(cached_requests, app_url, force_reload, repo_app, task)

def _sync_regular_apps(cached_requests, already_synchronized_app_urls, force_reload, single_app_url = None):
    app_urls = db.session.query(TranslatedApp.url).all()
    if single_app_url is not None:
        found = False
        for app_url, in app_urls:
            if app_url == single_app_url:
                found = True
                break
        if found:
            app_urls = [ (single_app_url,) ]
        else:
            app_urls = []
    tasks_list = []
    tasks_by_app_url = {}
    for app_url, in app_urls:
        if app_url not in already_synchronized_app_urls:
            task = MetadataTask(app_url, force_reload)
            tasks_list.append(task)
            tasks_by_app_url[app_url] = task

    RunInParallel(tasks_list).run()

    for app_url, in app_urls:
        if app_url not in already_synchronized_app_urls:
            _add_or_update_app(cached_requests, app_url, force_reload, repo_app = None, task = tasks_by_app_url[app_url])

def _add_or_update_app(cached_requests, app_url, force_reload, repo_app = None, task = None):
    now = datetime.datetime.utcnow()

    if DEBUG:
        logger.debug("Starting %s" % app_url)

    failing = False
    if task is None:
        try:
            metadata_information = extract_metadata_information(app_url, cached_requests, force_reload)
        except Exception:
            logger.warning("Error extracting information from %s" % app_url, exc_info = True)
            metadata_information = {}
            failing = True
    else:
        metadata_information = task.metadata_information or {}
        failing = task.failing

    if repo_app is not None:
        repo_app.translatable = metadata_information.get('translatable', False)
        repo_app.adaptable = metadata_information.get('adaptable', False)
        repo_app.original_translations = u','.join(metadata_information.get('original_translations', {}).keys())
        repo_app.last_change = now
        repo_app.last_check = now

        if failing:
            if not repo_app.failing:
                # Don't override if it was not failing before
                repo_app.failing_since = now
            repo_app.failing = True

        else:
            if repo_app.failing:
                repo_app.failing = False

    default_user = get_golab_default_user()

    if metadata_information.get('translatable'):
        translation_url = metadata_information.get('default_translation_url')
        original_messages = metadata_information['default_translations']
        default_metadata = metadata_information['default_metadata']
        for language, translated_messages in metadata_information['original_translations'].iteritems():
            add_full_translation_to_app(user = default_user, app_url = app_url, translation_url = translation_url, 
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
                add_full_translation_to_app(user = default_user, app_url = app_url, translation_url = translation_url,
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

                add_full_translation_to_app(user = default_user, app_url = app_url, translation_url = translation_url, 
                            app_metadata = default_metadata,
                            language = translation_bundle.language, target = translation_bundle.target, translated_messages = None,
                            original_messages = original_messages, from_developer = False)
                   

        translation_percent = retrieve_translations_percent(translation_url, original_messages)
        if repo_app is not None and translation_percent != repo_app.translation_percent:
            repo_app.translation_percent = json.dumps(translation_percent)
    
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise
    

ORIGIN_LANGUAGE = 'en'

def load_google_suggestions_by_lang(active_messages, language):
    """ Attempt to translate all the messages to a language """
    gs = goslate.Goslate()
    logger.info("Using Google Translator to use %s" % language)

    existing_suggestions = set([ human_key for human_key, in db.session.query(TranslationExternalSuggestion.human_key).filter_by(engine = 'google', language = language, origin_language = ORIGIN_LANGUAGE).all() ])

    missing_suggestions = active_messages - existing_suggestions
    print "Language:", language
    print list(active_messages)[:10], len(active_messages)
    print list(existing_suggestions)[:10], len(existing_suggestions)
    print "Missing:", len(missing_suggestions)
    counter = 0

    for message in missing_suggestions:
        if message.strip() == '':
            continue

        try:
            translated = gs.translate(message, language)
        except Exception as e:
            logger.warning("Google Translate stopped with exception: %s" % e, exc_info = True)
            return False, counter
        else:
            counter += 1

        if translated:
            suggestion = TranslationExternalSuggestion(engine = 'google', human_key = message, language = language, origin_language = ORIGIN_LANGUAGE, value = translated)
            db.session.add(suggestion)
            try:
                db.session.commit()
            except:
                db.session.rollback()
                raise
        else:
            logger.warning("Google Translate returned %r for message %r. Stopping." % (translated, message))
            return False, counter

    return True, counter


# ORDERED_LANGUAGES: first the semi official ones (less likely to have translations in Microsoft Translator API), then the official ones and then the rest
ORDERED_LANGUAGES = SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES + OFFICIAL_EUROPEAN_UNION_LANGUAGES + OTHER_LANGUAGES

def load_all_google_suggestions():
    active_messages = set([ value for value, in db.session.query(ActiveTranslationMessage.value).filter(TranslationBundle.language == 'en_ALL', ActiveTranslationMessage.bundle_id == TranslationBundle.id).all() ])
    
    total_counter = 0

    for language in ORDERED_LANGUAGES:
        should_continue, counter = load_google_suggestions_by_lang(active_messages, language)
        total_counter += counter
        if total_counter > 1000:
            logger.info("Stopping the google suggestions API after performing %s queries until the next cycle" % total_counter)
            break

        if not should_continue:
            logger.info("Stopping the google suggestions API until the next cycle")
            # There was an error: keep in the next iteration ;-)
            break

if __name__ == '__main__':
    from appcomposer import create_app
    my_app = create_app()
    with my_app.app_context():
        synchronize_apps_cache()
