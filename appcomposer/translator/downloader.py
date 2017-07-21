"""
There are two different processes related to the apps:

 1. Those downloading contents
 2. Those checking those contents

The files to be downloaded might be big, so might not be very good for storing in the database.

For this reason, we need a storage mechanism and we use redis for that.
"""
import zlib
import time
import json
import datetime
import threading
import traceback

import requests
from sqlalchemy.exc import SQLAlchemyError

from flask import current_app

from appcomposer import db, redis_store
from appcomposer.models import RepositoryApp
import appcomposer.translator.utils as trutils

from celery.utils.log import get_task_logger

GOLAB_REPO = u'golabz'
EXTERNAL_REPO = u'external'

logger = get_task_logger(__name__)

DEBUG = True
DEBUG_VERBOSE = False

def sync_repo_apps(force=False):
    """
    This script does not download anything related to the apps: it only checks golabz, and for repo app there, 
    it synchronizes the table RepositoryApp adding new apps, deleting expired ones or updating existing ones.

    It stores in redis the hash of the Go-Lab repos, so if there is no change, it does not need to look in the database.

    Optionally, if force=True, then it will still go through the process, but it is very unlikely that it is ever needed.
    """
    last_hash = redis_store.get('last_repo_apps_sync_hash')
    downloaded_apps, new_hash = _get_all_apps(last_hash)

    if not force:
        if new_hash == last_hash:
            return

    apps_by_repo_id = {
        # (repository, id): app
    }
    for app in downloaded_apps:
        apps_by_repo_id[app['repository'], unicode(app['id'])] = app

    stored_apps = db.session.query(RepositoryApp).all()
    stored_ids = []
    
    # 
    # Update or delete existing apps
    # 
    for repo_app in stored_apps:
        external_id = unicode(repo_app.external_id)
        if (repo_app.repository, external_id) in apps_by_repo_id:
            stored_ids.append(unicode(external_id))
            app = apps_by_repo_id[repo_app.repository, external_id]
            _update_existing_app(repo_app, app_url = app['app_url'], title = app['title'], app_thumb = app.get('app_thumb'), description = app.get('description'), app_image = app.get('app_image'), app_link = app.get('app_golabz_page'), repository = app['repository'])
        else:
            # Delete old apps (translations are kept, and the app is kept, but not listed in the repository apps)
            db.session.delete(repo_app)

    # 
    # Add new apps
    # 
    for app in downloaded_apps:
        if unicode(app['id']) not in stored_ids:
            # Double-check
            repo_app = db.session.query(RepositoryApp).filter_by(repository = app['repository'], external_id = app['id']).first()
            if repo_app is None:
                _add_new_app(repository = app['repository'], 
                            app_url = app['app_url'], title = app['title'], external_id = app['id'],
                            app_thumb = app.get('app_thumb'), description = app.get('description'),
                            app_image = app.get('app_image'), app_link = app.get('app_golabz_page'))

    try:
        db.session.commit()
    except SQLAlchemyError:
        logger.warning("Error upgrading apps", exc_info = True)
        db.session.rollback()
    else:
        redis_store.set('last_repo_apps_sync_hash', new_hash)
    finally:
        db.session.remove()

def download_repository_apps():
    """This method assumes that the table RepositoryApp is updated in a different process. 
    
    Therefore, it does not check in golabz, but just the database. The method itself is expensive, but can work in multiple threads processing all the requests.

    This method does not do anything with the translations in the database. It only updates the RepositoryApp table, storing it in the hard disk drive.

    Then, other methods can check on the RepositoryApp table to see if anything has changed since the last time it was checked. 
    Often, this will be "no", so no further database request will be needed.
    """
    
    repo_apps_by_id = {}
    tasks = []
    
    redis_key = 'appcomposer:repository:cache'

    stored_ids_in_redis = list(redis_store.hkeys(redis_key))

    for repo_app in db.session.query(RepositoryApp).all():
        task = MetadataTask(repo_app.id, repo_app.url, force_reload=False)
        repo_apps_by_id[repo_app.id] = repo_app
        tasks.append(task)
        if str(repo_app.id) in stored_ids_in_redis:
            stored_ids_in_redis.remove(str(repo_app.id))

    RunInParallel('Go-Lab repo', tasks).run()

    for key in stored_ids_in_redis:
        print("Deleting old {}".format(key))
        redis_store.hdel(redis_key, key)

    for task in tasks:
        repo_app = repo_apps_by_id[task.repo_id]
        repo_changes = False

        if task.failing:
            if not repo_app.failing:
                repo_app.failing = True
                repo_app.failing_since = datetime.datetime.utcnow()
                repo_changes = True

        else:
            if repo_app.failing:
                repo_app.failing = False
                repo_app.failing_since = None
                repo_changes = True

            current_hash = task.metadata_information['hash']
            if repo_app.downloaded_hash != current_hash:
                redis_store.hset(redis_key, repo_app.id, json.dumps(task.metadata_information))
                repo_app.downloaded_hash = current_hash
                repo_changes = True

        if repo_changes:
            repo_app.last_change = datetime.datetime.utcnow()

        repo_app.last_check = datetime.datetime.utcnow()

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
    else:
        db.session.remove()


#######################################################################################
# 
#   
#             CONCURRENCY
# 

class MetadataTask(threading.Thread):
    def __init__(self, repo_id, app_url, force_reload):
        threading.Thread.__init__(self)
        self.repo_id = repo_id
        self.cached_requests = trutils.get_cached_session(caching = not force_reload)
        self.app_url = app_url
        self.force_reload = force_reload
        self.finished = False
        self.failing = False
        self.metadata_information = None

    def run(self):
        self.failing = False
        try:
            self.metadata_information = trutils.extract_metadata_information(self.app_url, self.cached_requests, self.force_reload)
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
        print "Starting downloading {0} apps of {1}".format(len(self.tasks), self.tag)
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


#######################################################################################
# 
# 
# 
#             AUXILIAR METHODS 
# 
# 
#

def _add_new_app(repository, app_url, title, external_id, app_thumb, description, app_image, app_link):
    repo_app = RepositoryApp(name = title, url = app_url, external_id = external_id, repository = repository)
    repo_app.app_thumb = app_thumb
    repo_app.description = description
    repo_app.app_link = app_link
    repo_app.app_image = app_image
    db.session.add(repo_app)

def _update_existing_app(repo_app, app_url, title, app_thumb, description, app_image, app_link, repository):
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

def _get_all_apps(last_hash):
    all_golab_apps, new_hash = _get_golab_urls(last_hash)
    if all_golab_apps:
        all_golab_apps.extend(_get_other_apps())
    return all_golab_apps, new_hash

def _get_golab_urls(last_hash):
    try:
        apps_response = requests.get("http://www.golabz.eu/rest/apps/retrieve.json")
        apps_response.raise_for_status()
        apps_response_hash = unicode(zlib.crc32(apps_response.text))
        apps = apps_response.json()
    except requests.RequestException:
        logger.warning("Error retrieving applications from golabz", exc_info = True)
        return [], last_hash

    try:
        labs_response = requests.get("http://www.golabz.eu/rest/labs/retrieve.json")
        labs_response.raise_for_status()
        labs_response_hash = unicode(zlib.crc32(labs_response.text))
        labs = labs_response.json()
    except requests.RequestException:
        logger.warning("Error retrieving laboratories from golabz", exc_info = True)
        return [], last_hash

    current_hash = apps_response_hash + labs_response_hash
    if current_hash == last_hash:
        logger.warning("No change in golabz (same hash)")
        return [], last_hash

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

    return apps, current_hash

def _get_other_apps():
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

    OTHER_APPS = current_app.config.get('OTHER_APPS', [])
    OTHER_APPS.append(GRAASP)
    OTHER_APPS.append(TWENTE_COMMONS)
    if current_app.config['DEBUG']:
        TWENTE_COMMONS['app_url'] = 'http://localhost:5000/twente_commons/'

    return OTHER_APPS
