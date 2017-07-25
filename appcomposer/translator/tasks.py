import os
import sys
import datetime
from celery.schedules import crontab

from celery import Celery
from celery.utils.log import get_task_logger

cwd = os.getcwd()
path = os.path.join("appcomposer", "translator")
if cwd.endswith(path):
    cwd = cwd[0:len(cwd) - len(path)]
    os.chdir(cwd)

sys.path.insert(0, cwd)


GOLAB_REPO = u'golabz'
EXTERNAL_REPO = u'external'

DEBUG = True

logger = get_task_logger(__name__)

cel = Celery('pusher_tasks', backend='redis', broker='redis://localhost:6379/6')

cel.conf.update(
    worker_prefetch_multiplier=4,
    worker_concurrency=4,
    task_acks_late="1",
    task_ignore_resultLT=True,
    task_serializer='json',


    beat_schedule = {
#         'synchronize_apps_cache': {
#             'task': 'synchronize_apps_cache',
#             'schedule': datetime.timedelta(minutes=5),
#             'args': ()
#         },
#         'synchronize_apps_no_cache': {
#             'task': 'synchronize_apps_no_cache',
#             'schedule': crontab(hour=3, minute=0),
#             'args': ()
#         },
        'load_google_suggestions' : {
            'task' : 'load_google_suggestions',
            'schedule' : crontab(hour=5, minute=0),
            'args' : ()
        },
        'delete_old_realtime_active_users' : {
            'task' : 'delete_old_realtime_active_users',
            'schedule' : datetime.timedelta(hours = 1),
            'args' : ()
        },
        'notify_changes' : {
            'task' : 'notify_changes',
            'schedule' : datetime.timedelta(minutes = 5),
            'args' : ()
        },
        'sync_mongodb_recent': {
            'task' : 'sync_mongodb_recent',
            'schedule' : datetime.timedelta(minutes = 2),
            'args' : ()
        },
        'sync_mongodb_all': {
            'task' : 'sync_mongodb_all',
            'schedule' : crontab(hour=5, minute=30),
            'args' : ()
        },
        'sync_repo_apps_cached': {
            'task' : 'sync_repo_apps_cached',
            'schedule' : datetime.timedelta(minutes = 5),
            'args' : ()
        },
        'sync_repo_apps_all': {
            'task' : 'sync_repo_apps_all',
            'schedule' : crontab(hour=5, minute=0),
            'args' : ()
        },
    },

    task_routes = {
        # 
        # The following are tasks that are probably non-blocking and can be run in parallel and are not critical
        # 
        'load_google_suggestions': {
            'queue': 'non-critical-independent-tasks',
        },
        'delete_old_realtime_active_users': {
            'queue': 'non-critical-independent-tasks',
        },
        
        # 
        # The following are tasks which must be quick but still independent
        # 
        'notify_changes' : {
            'queue': 'critical-independent-tasks',
        },
        'sync_mongodb_recent' : {
            'queue': 'critical-independent-tasks',
        },
        'sync_repo_apps_cached': {
            'queue': 'critical-independent-tasks',
        },
        'download_repository_single_app': {   # Only called from outside
            'queue': 'critical-independent-tasks',
        },

        # The following are tasks which can be slow but still independent
        # 
        'sync_mongodb_all' : {
            'queue': 'slow-independent-tasks',
        },
        'sync_repo_apps_all': {
            'queue': 'slow-independent-tasks',
        },
        'download_repository_apps': {
            'queue': 'slow-independent-tasks',
        },

        # The following are tasks which can only be run in a single queue
        # TODO: process_single_app  # when called
        # TODO: process_latest_apps # e.g., every 5 minute
        # TODO: process_all_apps    # e.g., once a day
    }
)


from appcomposer import app as my_app, db
from appcomposer.models import TranslationCurrentActiveUser
from appcomposer.translator.translation_listing import synchronize_apps_cache, synchronize_apps_no_cache, load_all_google_suggestions
from appcomposer.translator.mongodb_pusher import sync_mongodb_all, sync_mongodb_last_hour
from appcomposer.translator.notifications import run_notifications
from appcomposer.translator.downloader import sync_repo_apps, download_repository_apps, download_repository_single_app

@cel.task(name='notify_changes', bind=True)
def task_notify_changes(self):
    with my_app.app_context():
        return run_notifications()

@cel.task(name='synchronize_apps_cache', bind=True)
def synchronize_apps_cache_wrapper(self, source = None, single_app_url = None):
    if source is None:
        source = 'scheduled'

    with my_app.app_context():
        result = synchronize_apps_cache(source = source, single_app_url = single_app_url)
    sync_mongodb_last_hour(self)
    return result

@cel.task(name='synchronize_apps_no_cache', bind=True)
def synchronize_apps_no_cache_wrapper(self, source = None, single_app_url = None, must_sync = True):
    if source is None:
        source = 'scheduled'
    with my_app.app_context():
        result = synchronize_apps_no_cache(source = source, single_app_url = single_app_url)
    if must_sync:
        sync_mongodb_all(self)
    return result

@cel.task(name="sync_mongodb_recent", bind=True)
def task_sync_mongodb_recent(self):
    return sync_mongodb_last_hour(self)

@cel.task(name="sync_mongodb_all", bind=True)
def task_sync_mongodb_all(self):
    return sync_mongodb_all(self)

@cel.task(name='load_google_suggestions', bind=True)
def task_load_google_suggestions(self):
    with my_app.app_context():
        load_all_google_suggestions()

@cel.task(name='delete_old_realtime_active_users', bind=True)
def task_delete_old_realtime_active_users(self):
    with my_app.app_context():
        two_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours = 2)
        old_active_users = db.session.query(TranslationCurrentActiveUser).filter(TranslationCurrentActiveUser.last_check < two_hours_ago).all()
        for old_active_user in old_active_users:
            db.session.delete(old_active_user)
        if len(old_active_users):
            try:
                db.session.commit()
            except:
                db.session.rollback()
                raise

@cel.task(name='sync_repo_apps_cached', bind=True)
def task_sync_repo_apps_cached(self):
    with my_app.app_context():
        changes = sync_repo_apps(force=False)
        if changes:
            task_download_repository_apps.delay()


@cel.task(name='sync_repo_apps_all', bind=True)
def task_sync_repo_apps_all(self):
    with my_app.app_context():
        changes = sync_repo_apps(force=True)
        if changes:
            task_download_repository_apps.delay()


@cel.task(name='download_repository_single_app', bind=True)
def task_download_repository_single_app(self, app_url):
    with my_app.app_context():
        changes = download_repository_single_app(app_url)
        if changes:
            task_sync_mongodb_recent.delay()

@cel.task(name='download_repository_apps', bind=True)
def task_download_repository_apps(self):
    with my_app.app_context():
        changes = download_repository_apps()
        if changes:
            task_sync_mongodb_recent.delay()

