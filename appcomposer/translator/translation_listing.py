import time
import json
import random
import datetime
import threading
import traceback

import goslate
import requests

from sqlalchemy.exc import SQLAlchemyError
from celery.utils.log import get_task_logger

from appcomposer.application import app
from appcomposer.db import db
from appcomposer.models import RepositoryApp, TranslatedApp, ActiveTranslationMessage, TranslationBundle, TranslationUrl, TranslationExternalSuggestion

from appcomposer.languages import SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES, OFFICIAL_EUROPEAN_UNION_LANGUAGES, OTHER_LANGUAGES
from appcomposer.translator.utils import extract_metadata_information
import appcomposer.translator.utils as trutils
from appcomposer.translator.ops import add_full_translation_to_app, retrieve_translations_percent, get_golab_default_user, start_synchronization, end_synchronization, get_bundles_by_key_namespaces

GOLAB_REPO = u'golabz'
EXTERNAL_REPO = u'external'

GRAASP = {
    'title': 'Graasp',
    'id': '2',
    'description': "Graasp is the ILS platform",
    'app_url': "http://composer.golabz.eu/graasp_i18n/",
    'app_type': "OpenSocial gadget",
    'app_image': "http://composer.golabz.eu/static/img/graasp-logo.png",
    'app_thumb': "http://composer.golabz.eu/static/img/graasp-logo-thumb.png",
    'app_golabz_page': "http://graasp.eu/",
    'repository': "Go-Lab ecosystem",
}

TWENTE_COMMONS = {
    'title': 'Twente commons',
    'id': '1',
    'description': "Many tools developed by UTwente share many commons. For your convenience, these terms are centralized in a single translation here.",
    'app_url': "http://composer.golabz.eu/twente_commons/",
    'app_type': "OpenSocial gadget",
    'app_image': "http://composer.golabz.eu/static/img/twente.jpg",
    'app_thumb': "http://composer.golabz.eu/static/img/twente-thumb.jpg",
    'app_golabz_page': "http://go-lab.gw.utwente.nl/production/",
    'repository': "Go-Lab ecosystem",
}

OTHER_APPS = app.config.get('OTHER_APPS', [])
OTHER_APPS.append(GRAASP)
OTHER_APPS.append(TWENTE_COMMONS)

if False: # ONLY FOR TESTING
    OTHER_APPS.append({
        'title' : 'Testing',
        'id' : '3',
        'description' : "Foo",
        'app_url' : 'http://localhost:5000/embed/apps/b19200d2-965b-4b74-8e4a-1642fbc721c5/app.xml',
        'app_type': "OpenSocial gadget",
        'app_image': "http://composer.golabz.eu/static/img/twente.jpg",
        'app_thumb': "http://composer.golabz.eu/static/img/twente-thumb.jpg",
        'app_golabz_page': "http://go-lab.gw.utwente.nl/production/",
        'repository': "Go-Lab ecosystem",
    })

DEBUG = True
DEBUG_VERBOSE = False

logger = get_task_logger(__name__)

def get_other_apps():
    if app.config['DEBUG']:
        TWENTE_COMMONS['app_url'] = 'http://localhost:5000/twente_commons/'
    return OTHER_APPS

def synchronize_apps_cache(source, single_app_url = None):
    """Force obtaining the results and checking everything again to avoid inconsistences. 
    This can safely be run every few minutes, since most applications will be in the cache."""
    sync_id = start_synchronization(source = source, cached = True, single_app_url = single_app_url)
    number = 0
    try:
        cached_requests = trutils.get_cached_session()
        synced_apps = []
        all_golab_apps = _get_golab_translations(cached_requests)
        all_golab_apps.extend(get_other_apps())
        number += _sync_translations(cached_requests, "Go-Lab apps", synced_apps, all_golab_apps, force_reload = False, single_app_url = single_app_url)
        number += _sync_regular_apps(cached_requests, synced_apps, force_reload = False, single_app_url = single_app_url)
    finally:
        end_synchronization(sync_id, number)
    
def synchronize_apps_no_cache(source, single_app_url = None):
    """Force obtaining the results and checking everything again to avoid inconsistences. This should be run once a day."""
    sync_id = start_synchronization(source = source, cached = False, single_app_url = single_app_url)
    number = 0
    try:
        cached_requests = trutils.get_cached_session(caching = False)
        synced_apps = []
        all_golab_apps = _get_golab_translations(cached_requests)
        all_golab_apps.extend(get_other_apps())
        number += _sync_translations(cached_requests, "Go-Lab apps", synced_apps, all_golab_apps, force_reload = True, single_app_url = single_app_url)
        number += _sync_regular_apps(cached_requests, synced_apps, force_reload = True, single_app_url = single_app_url)
    finally:
        end_synchronization(sync_id, number)

class MetadataTask(threading.Thread):
    def __init__(self, app_url, force_reload):
        threading.Thread.__init__(self)
        self.cached_requests = trutils.get_cached_session(caching = not force_reload)
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
            if DEBUG_VERBOSE:
                print("Error extracting information from %s" % self.app_url)
                traceback.print_exc()
            self.metadata_information = {}
            self.failing = True
        else:
            self.failing = self.metadata_information.get('failing', False)
        self.finished = True

class RunInParallel(object):
    def __init__(self, tag, tasks, thread_number = 15):
        self.tag = tag
        self.tasks = tasks
        self.thread_number = thread_number

    def all_finished(self):
        for task in self.tasks:
            if not task.finished:
                return False
        return True

    def run(self):
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

        print "All {0} apps of {1} downloaded".format(len(self.tasks), self.tag)

def _sync_translations(cached_requests, tag, synced_apps, apps_to_process, force_reload, single_app_url = None):
    if single_app_url is not None:
        app_found = None
        for app in apps_to_process:
            if app['app_url'] == single_app_url:
                app_found = app
                break
        if app_found is None:
            return 0

        apps = [ app_found ]
    else:
        apps = apps_to_process

    # Don't consider synced_apps
    apps = [ app for app in apps if app['app_url'] not in synced_apps ]

    # 
    # Now apps is the list of applications (and single_app_url can be forgotten)
    # 
    apps_by_repo_id = {
        # (repository, id): app
    }
    for app in apps:
        apps_by_repo_id[app['repository'], unicode(app['id'])] = app

    apps_by_url = {
        # url: app
    }
    for app in apps:
        apps_by_url[app['app_url']] = app
    
    tasks_list = []
    tasks_by_app_url = {}
    for app_url in apps_by_url:
        task = MetadataTask(app_url, force_reload)
        tasks_list.append(task)
        tasks_by_app_url[app_url] = task
    
    run_in_parallel = RunInParallel(tag, tasks_list)
    run_in_parallel.run()

    stored_apps = db.session.query(RepositoryApp).all()
    stored_ids = []

    for repo_app in stored_apps:
        external_id = unicode(repo_app.external_id)
        try:
            if (repo_app.repository, external_id) in apps_by_repo_id:
                stored_ids.append(unicode(external_id))
                app = apps_by_repo_id[repo_app.repository, external_id]
                _update_existing_app(cached_requests, repo_app, app_url = app['app_url'], title = app['title'], app_thumb = app.get('app_thumb'), description = app.get('description'), app_image = app.get('app_image'), app_link = app.get('app_golabz_page'), force_reload = force_reload, task = tasks_by_app_url.get(app['app_url']), repository = app['repository'])
            else:
                if len(apps) > 1:
                    # Delete old apps (translations are kept, and the app is kept, but not listed in the repository apps)
                    db.session.delete(repo_app)
                    try:
                        db.session.commit()
                    except:
                        db.session.rollback()
                        raise

        except SQLAlchemyError:
            # One error in one application shouldn't stop the process
            logger.warning("Error updating or deleting app %s" % app['app_url'], exc_info = True)
            continue

    # 
    # Add new apps
    # 
    for app in apps:
        if unicode(app['id']) not in stored_ids:
            try:
                # Double-check
                repo_app = db.session.query(RepositoryApp).filter_by(repository = app['repository'], external_id = app['id']).first()
                if repo_app is None:
                    _add_new_app(cached_requests, repository = app['repository'], 
                                app_url = app['app_url'], title = app['title'], external_id = app['id'],
                                app_thumb = app.get('app_thumb'), description = app.get('description'),
                                app_image = app.get('app_image'), app_link = app.get('app_golabz_page'),
                                force_reload = force_reload, task = tasks_by_app_url.get(app['app_url']))
            except SQLAlchemyError:
                logger.warning("Error adding app %s" % app['app_url'], exc_info = True)
                continue
   
        # Anyway...
        synced_apps.append(app['app_url'])
    
    return len(tasks_list)

def _get_golab_translations(cached_requests):
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
        lab_title = current_lab['title']
        for pos, internal_lab in enumerate(lab.get('lab_apps', [])):
            current_lab = current_lab.copy()
            current_lab['id'] = '%s-%s' % (lab_id, pos)
            current_lab['app_url'] = internal_lab['app_url']
            if current_lab['app_url']:
                if not current_lab['app_url'].startswith('http://') and not current_lab['app_url'].startswith('https://'):
                    current_lab['app_url'] = 'http://{0}'.format(current_lab['app_url'])
            if len(lab.get('lab_apps', [])) > 1:
                current_lab['title'] = u"{0} ({1})".format(lab_title, internal_lab['app_title'])
            current_lab['app_type'] = internal_lab['app_type']
            labs_adapted.append(current_lab)

    apps.extend(labs_adapted)
    for app in apps:
        app['repository'] = GOLAB_REPO
        if app['app_url']:
            app_url = app['app_url']
            if not app_url.startswith('http://') and not app_url.startswith('https://'):
                app['app_url'] = 'http://{0}'.format(app_url)

    return apps
    

def _update_existing_app(cached_requests, repo_app, app_url, title, app_thumb, description, app_image, app_link, force_reload, task, repository = None):
    if repo_app.name != title:
        repo_app.name = title
    if repo_app.url != app_url:
        repo_app.url = app_url
    if repo_app.app_thumb != app_thumb:
        repo_app.app_thumb = app_thumb
    if repo_app.description != description:
        repo_app.description = description
    if repo_app.app_link != app_link:
        repo_app.app_link = app_link
    if repo_app.app_image != app_image:
        repo_app.app_image = app_image
    if repository is not None and repo_app.repository != repository:
        repo_app.repository = repository

    _add_or_update_app(cached_requests, app_url, force_reload, repo_app, task)

def _add_new_app(cached_requests, repository, app_url, title, external_id, app_thumb, description, app_image, app_link, force_reload, task):
    repo_app = RepositoryApp(name = title, url = app_url, external_id = external_id, repository = repository)
    repo_app.app_thumb = app_thumb
    repo_app.description = description
    repo_app.app_link = app_link
    repo_app.app_image = app_image
    db.session.add(repo_app)

    _add_or_update_app(cached_requests, app_url, force_reload, repo_app, task)

def _sync_regular_apps(cached_requests, synced_apps, force_reload, single_app_url = None):
    app_urls = [ app_url for app_url, in db.session.query(TranslatedApp.url).all() ]
    if single_app_url is not None:
        if single_app_url in app_urls and single_app_url not in synced_apps:
            app_urls = [ single_app_url ]
        else:
            return 0

    tasks_list = []
    tasks_by_app_url = {}
    for app_url in app_urls:
        if app_url not in synced_apps:
            task = MetadataTask(app_url, force_reload)
            tasks_list.append(task)
            tasks_by_app_url[app_url] = task

    if len(tasks_list) == 0:
        return 0

    RunInParallel("Regular apps", tasks_list).run()

    for app_url in app_urls:
        if app_url not in synced_apps:
            _add_or_update_app(cached_requests, app_url, force_reload, repo_app = None, task = tasks_by_app_url[app_url])

    return len(app_urls)

def _add_or_update_app(cached_requests, app_url, force_reload, repo_app = None, task = None):
    now = datetime.datetime.utcnow()

    if DEBUG:
        logger.debug("Starting %s" % app_url)

    failing = False
    if task is None:
        try:
            metadata_information = extract_metadata_information(app_url, cached_requests, force_reload)
        except Exception:
            if DEBUG_VERBOSE:
                print("Error on %s" % app_url)
                traceback.print_exc()
            logger.warning("Error extracting information from %s" % app_url, exc_info = True)
            metadata_information = {}
            failing = True
    else:
        metadata_information = task.metadata_information or {}
        failing = task.failing

    if repo_app is not None:
        if metadata_information.get('translatable') and len(metadata_information.get('default_translations', [])) > 0:
            repo_app.translatable = True
        else:
            # If it is translatable but there is no default translation; don't take it into account
            repo_app.translatable = False
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

def load_google_suggestions_by_lang(active_messages, language, origin_language = None):
    """ Attempt to translate all the messages to a language """
    
    if origin_language is None:
        origin_language = ORIGIN_LANGUAGE

    gs = goslate.Goslate()
    logger.info("Using Google Translator to use %s" % language)

    existing_suggestions = set([ human_key for human_key, in db.session.query(TranslationExternalSuggestion.human_key).filter_by(engine = 'google', language = language, origin_language = origin_language).all() ])

    missing_suggestions = active_messages - existing_suggestions
    print "Language:", language
    print list(active_messages)[:10], len(active_messages)
    print list(existing_suggestions)[:10], len(existing_suggestions)
    print "Missing:", len(missing_suggestions)
    missing_suggestions = list(missing_suggestions)
    random.shuffle(missing_suggestions)
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
            suggestion = TranslationExternalSuggestion(engine = 'google', human_key = message, language = language, origin_language = origin_language, value = translated)
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

def _load_all_google_suggestions(from_language, to_languages):
    active_messages = set([ value for value, in db.session.query(ActiveTranslationMessage.value).filter(TranslationBundle.language == '{0}_ALL'.format(from_language), ActiveTranslationMessage.bundle_id == TranslationBundle.id).all() ])
    
    total_counter = 0

    for language in to_languages:
        should_continue, counter = load_google_suggestions_by_lang(active_messages, language)
        total_counter += counter
        if total_counter > 1000:
            logger.info("Stopping the google suggestions API after performing %s queries until the next cycle" % total_counter)
            break

        if not should_continue:
            logger.info("Stopping the google suggestions API until the next cycle")
            # There was an error: keep in the next iteration ;-)
            break


def load_all_google_suggestions():
    # First try to create suggestions from English to all the languages
    _load_all_google_suggestions('en', ORDERED_LANGUAGES)

    # Then, try to create suggestions all the languages to English for developers
    for language in ORDERED_LANGUAGES:
        _load_all_google_suggestions(language, ['en'])

if __name__ == '__main__':
    from appcomposer import create_app
    my_app = create_app()
    with my_app.app_context():
        synchronize_apps_cache()
