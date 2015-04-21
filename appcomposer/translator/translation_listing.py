import sys
import time
import json
import datetime
import threading

import requests
from sqlalchemy.exc import SQLAlchemyError
from celery.utils.log import get_task_logger

from appcomposer.application import app
from appcomposer.db import db
from appcomposer.models import RepositoryApp, TranslatedApp
from appcomposer.translator.utils import get_cached_session, extract_metadata_information
from appcomposer.translator.ops import add_full_translation_to_app, retrieve_translations_percent, get_golab_default_user, start_synchronization, end_synchronization

GOLAB_REPO = u'golabz'
EXTERNAL_REPO = u'external'

DEBUG = True

logger = get_task_logger(__name__)

def synchronize_apps_cache():
    """Force obtaining the results and checking everything again to avoid inconsistences. 
    This can safely be run every few minutes, since most applications will be in the cache."""
    sync_id = start_synchronization()
    try:
        cached_requests = get_cached_session()
        synced_apps = _sync_golab_translations(cached_requests, force_reload = False)
        _sync_regular_apps(cached_requests, synced_apps, force_reload = False)
    finally:
        end_synchronization(sync_id)
    
def synchronize_apps_no_cache():
    """Force obtaining the results and checking everything again to avoid inconsistences. This should be run once a day."""
    sync_id = start_synchronization()
    try:
        cached_requests = get_cached_session()
        synced_apps = _sync_golab_translations(cached_requests, force_reload = True)
        _sync_regular_apps(cached_requests, synced_apps, force_reload = True)
    finally:
        end_synchronization(sync_id)

class MetadataTask(threading.Thread):
    def __init__(self, app_url, force_reload):
        threading.Thread.__init__(self)
        self.cached_requests = get_cached_session()
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

def _sync_golab_translations(cached_requests, force_reload):
    try:
        apps_response = cached_requests.get("http://www.golabz.eu/rest/apps/retrieve.json")
        apps_response.raise_for_status()
        apps = apps_response.json()
    except requests.RequestException:
        logger.warning("Error retrieving applications from golabz", exc_info = True)
        return []

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
                # Delete old apps (translations are kept, and the app is kept, but not listed in the repository apps)
                db.session.delete(repo_app)
                db.session.commit()
            else:
                stored_ids.append(external_id)
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
        if app['id'] not in stored_ids:
            try:
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

def _sync_regular_apps(cached_requests, already_synchronized_app_urls, force_reload):
    app_urls = db.session.query(TranslatedApp.url).all()
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
    now = datetime.datetime.now()

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
            repo_app.failing = True
            repo_app.failing_since = now
        else:
            repo_app.failing = False

    default_user = get_golab_default_user()

    if metadata_information.get('translatable'):
        translation_url = metadata_information.get('default_translation_url')
        original_messages = metadata_information['default_translations']
        for language, translated_messages in metadata_information['original_translations'].iteritems():
            add_full_translation_to_app(user = default_user, app_url = app_url, translation_url = translation_url, 
                                language = language, target = u'ALL', translated_messages = translated_messages, 
                                original_messages = original_messages, from_developer = True)

        translation_percent = retrieve_translations_percent(translation_url, original_messages)
        if repo_app is not None:
            repo_app.translation_percent = json.dumps(translation_percent)
    
    db.session.commit()
    
if __name__ == '__main__':
    from appcomposer import app as my_app
    with my_app.app_context():
        synchronize_apps_cache()
