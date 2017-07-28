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
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from flask import current_app

from appcomposer import db, redis_store
from appcomposer.models import RepositoryApp
import appcomposer.translator.utils as trutils
from appcomposer.translator.ops import calculate_content_hash
from appcomposer.translator.extractors import extract_metadata_information

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

    It return True if there was any change
    """
    last_hash = redis_store.get('last_repo_apps_sync_hash')
    downloaded_apps, new_hash = _get_all_apps(last_hash)

    if not downloaded_apps:
        # An error ocurred in the apps
        return False

    if not force:
        if new_hash == last_hash:
            return False

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
        return False
    else:
        redis_store.set('last_repo_apps_sync_hash', new_hash)
    finally:
        db.session.remove()

    return last_hash == new_hash


_REDIS_CACHE_KEY = 'appcomposer:repository:cache'

def download_repository_apps():
    """This method assumes that the table RepositoryApp is updated in a different process. 
    
    Therefore, it does not check in golabz, but just the database. The method itself is expensive, but can work in multiple threads processing all the requests.

    This method does not do anything with the translations in the database. It only updates the RepositoryApp table, storing it in redis.

    Then, other methods can check on the RepositoryApp table to see if anything has changed since the last time it was checked. 
    Often, this will be "no", so no further database request will be needed.
    """
    
    repo_apps_by_id = {}
    tasks = []

    stored_ids_in_redis = list(redis_store.hkeys(_REDIS_CACHE_KEY))

    for repo_app in db.session.query(RepositoryApp).all():
        task = _MetadataTask(repo_app.id, repo_app.url, force_reload=False)
        repo_apps_by_id[repo_app.id] = repo_app
        tasks.append(task)
        if str(repo_app.id) in stored_ids_in_redis:
            stored_ids_in_redis.remove(str(repo_app.id))

    _RunInParallel('Go-Lab repo', tasks).run()

    for key in stored_ids_in_redis:
        redis_store.hdel(_REDIS_CACHE_KEY, key)

    app_changes = False
    for task in tasks:
        repo_app = repo_apps_by_id[task.repo_id]
        if _update_repo_app(task=task, repo_app=repo_app):
            app_changes = True

    try:
        db.session.commit()
    except SQLAlchemyError:
        logger.warning("Error downloading repo", exc_info = True)
        db.session.rollback()
        return False
    else:
        db.session.remove()

    return app_changes


def download_repository_single_app(app_url):
    """
    This method does the same as the previous one, but with a single URL (therefore not checking more variables, neither starting more than 1 thread, and without adding new or deleting apps).
    It returns if there was a change
    """
    
    repo_app = db.session.query(RepositoryApp).filter_by(url=app_url).first()
    if repo_app is None:
        raise Exception("App URL not in the repository: {}".format(app_url))

    task = _MetadataTask(repo_app.id, repo_app.url, force_reload=False)

    _RunInParallel('Go-Lab repo', [ task ], thread_number=1).run()

    changes = _update_repo_app(task=task, repo_app=repo_app)

    try:
        db.session.commit()
    except SQLAlchemyError:
        logger.warning("Error downloading single app: {}".format(app_url), exc_info = True)
        db.session.rollback()
        return False
    else:
        db.session.remove()

    return changes

def update_content_hash(app_url):
    """Given an App URL generate the hash of the values of the translations. This way, can quickly know if an app was changed or not in a single query, and not do the whole
    expensive DB processing for those which have not changed."""
    contents_hash = calculate_content_hash(app_url)
    if contents_hash:
        repo_app = db.session.query(RepositoryApp).filter_by(url=app_url).first()
        if repo_app:
            if repo_app.contents_hash != contents_hash:
                repo_app.contents_hash = contents_hash
                repo_app.last_change = datetime.datetime.utcnow()

                try:
                    db.session.commit()
                except SQLAlchemyError as e:
                    logger.warning("Error updating content hash for {}: {}".format(app_url, e), exc_info = True)
                    db.session.rollback()
                    return False
                else:
                    db.session.remove()

def retrieve_updated_translatable_apps():
    """This method collects information previously stored by other process into Redis, and returns only those apps which have changed, are translatable and not currently failing"""  
    return _retrieve_translatable_apps(query = db.session.query(RepositoryApp).filter(
                        RepositoryApp.translatable == True,                                  # Only translatable pages
                        RepositoryApp.failing == False,                                      # Which are not failing
                        or_(
                            # If it has never been processed
                            RepositoryApp.last_processed_downloaded_hash == None,
                            RepositoryApp.last_processed_contents_hash == None,
                            # or if they have changed somewhere:
                            RepositoryApp.last_processed_downloaded_hash != RepositoryApp.downloaded_hash,  # Either when downloading
                            RepositoryApp.last_processed_contents_hash != RepositoryApp.contents_hash,  # Or either by a user changing something
                        )
                ))

def retrieve_all_translatable_apps():
    """This method collects information previously stored by other process into Redis, and returns only those apps which are translatable and not currently failing"""  
    return _retrieve_translatable_apps(query = db.session.query(RepositoryApp).filter(
                        RepositoryApp.translatable == True,                                  # Only translatable pages
                        RepositoryApp.failing == False,                                      # Which are not failing
                ))

def retrieve_single_translatable_apps(app_url):
    """This method collects information previously stored by other process into Redis, and returns only those apps which are translatable and not currently failing"""  
    return _retrieve_translatable_apps(query = db.session.query(RepositoryApp).filter(
                        RepositoryApp.translatable == True,                                  # Only translatable pages
                        RepositoryApp.failing == False,                                      # Which are not failing
                        RepositoryApp.url == app_url,                                        # Only one
                ))

#######################################################################################
# 
#   
#             CONCURRENCY
# 

class _MetadataTask(threading.Thread):
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

class _RunInParallel(object):
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

def _retrieve_translatable_apps(query):
    contents = [
        # app_id: repo_app.id
        # app_url: repo_app.url
        # metadata: {
        #      metadata contents retrieved from Redis
        # }
    ]
    for repo_app in query.all():
        app_metadata = redis_store.hget(_REDIS_CACHE_KEY, repo_app.id)
        if app_metadata is not None:
            contents.append({
                'app_id': repo_app.id,
                'app_url': repo_app.url,
                'metadata': json.loads(app_metadata),
            })

    return contents

def _update_repo_app(task, repo_app):
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

        current_hash = task.metadata_information.pop('hash')
        if repo_app.downloaded_hash != current_hash:
            previous_contents = redis_store.hget(_REDIS_CACHE_KEY, repo_app.id)
            previous_hash = repo_app.downloaded_hash
            new_contents = json.dumps(task.metadata_information)
            redis_store.hset(_REDIS_CACHE_KEY, repo_app.id, new_contents)
            repo_app.downloaded_hash = current_hash

            if task.metadata_information.get('translatable') and len(task.metadata_information.get('default_translations', [])) > 0:
                repo_app.translatable = True
            else:
                # If it is translatable but there is no default translation; don't take it into account
                repo_app.translatable = False

            repo_app.adaptable = task.metadata_information.get('adaptable', False)
            repo_app.original_translations = u','.join(task.metadata_information.get('original_translations', {}).keys())

            repo_changes = True
    
            redis_store.rpush('appcomposer:downloader:changes', repo_app.url)

        else: # same hash, still check (if redis was restarted or something, the database will say that it's gone while it's not)
            current_contents = redis_store.hget(_REDIS_CACHE_KEY, repo_app.id)
            if current_contents is None:
                redis_store.hset(_REDIS_CACHE_KEY, repo_app.id, json.dumps(task.metadata_information))
                repo_changes = True

    if repo_changes:
        repo_app.last_change = datetime.datetime.utcnow()
        repo_app.last_download_change = datetime.datetime.utcnow()

    repo_app.last_check = datetime.datetime.utcnow()

    return repo_changes


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
    rsession = requests.Session()
    try:
        apps_response = rsession.get("http://www.golabz.eu/rest/apps/retrieve.json")
        apps_response.raise_for_status()
        apps_response_hash = unicode(zlib.crc32(apps_response.text))
        apps = apps_response.json()
    except requests.RequestException:
        logger.warning("Error retrieving applications from golabz", exc_info = True)
        return [], last_hash

    try:
        labs_response = rsession.get("http://www.golabz.eu/rest/labs/retrieve.json")
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

    if current_app.debug:
        if False: # ONLY FOR TESTING
            OTHER_APPS.append({
                'title' : 'Testing',
                'id' : '3',
                'description' : "Foo",
                'app_url' : 'http://localhost/testing/app.xml',
                'app_type': "OpenSocial gadget",
                'app_image': "http://composer.golabz.eu/static/img/twente.jpg",
                'app_thumb': "http://composer.golabz.eu/static/img/twente-thumb.jpg",
                'app_golabz_page': "http://go-lab.gw.utwente.nl/production/",
                'repository': "Go-Lab ecosystem",
            })

    if current_app.config['DEBUG']:
        TWENTE_COMMONS['app_url'] = 'http://localhost:5000/twente_commons/'

    return OTHER_APPS

