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

from appcomposer import app as my_app, db
from appcomposer.translator.translation_listing import synchronize_apps_cache, synchronize_apps_no_cache, synchronize_single_app_no_cached
from appcomposer.translator.suggestions import load_all_google_suggestions, load_all_deepl_suggestions, load_all_microsoft_suggestions
from appcomposer.translator.mongodb_pusher import sync_mongodb_all, sync_mongodb_last_hour
from appcomposer.translator.notifications import run_notifications, run_update_notifications
from appcomposer.translator.downloader import sync_repo_apps, download_repository_apps, download_repository_single_app, update_content_hash, update_check_urls_status
from appcomposer.translator.ops import start_synchronization, end_synchronization


GOLAB_REPO = u'golabz'
EXTERNAL_REPO = u'external'

DEBUG = True

logger = get_task_logger(__name__)

cel = Celery('pusher_tasks', backend='redis', broker='redis://localhost:6379/6')

NON_CRITICAL_INDEPENDENT_TASKS = 'non-critical-independent-tasks'
CRITICAL_INDEPENDENT_TASKS = 'critical-independent-tasks'
SLOW_INDEPENDENT_TASKS = 'slow-independent-tasks'
SINGLE_SYNC_TASKS = 'single-sync-tasks'

cel.conf.update(
    worker_prefetch_multiplier=4,
    worker_concurrency=4,
    task_acks_late="1",
    task_ignore_result=True,
    task_serializer='json',


    beat_schedule = {
        'notify_changes' : {
            'task' : 'notify_changes',
            'schedule' : datetime.timedelta(minutes = 5),
            'args' : ()
        },
        'notify_updates' : {
            'task' : 'notify_updates',
            'schedule' : datetime.timedelta(minutes = 1),
            'args' : ()
        },
        'synchronize_apps_cache': { # This must be triggered even if there is no change in the contents
            'task': 'synchronize_apps_cache',
            'schedule': datetime.timedelta(minutes=4),
            'args': ()
        },
        'download_repository_apps': { # This triggers synchronize_apps_cache too, but only if a change in the original contents
            'task': 'download_repository_apps',
            'schedule': datetime.timedelta(minutes=4),
            'args': ()
        },
        'sync_repo_apps_cached': { # This triggers download_repository_apps too, but only if a change in the golabz repo
            'task' : 'sync_repo_apps_cached',
            'schedule' : datetime.timedelta(minutes=4),
            'args' : ()
        },

        # Crontab-based tasks: slow tasks at night
        'sync_repo_apps_all': {
            'task' : 'sync_repo_apps_all',
            'schedule' : crontab(hour=3, minute=30),
            'args' : ()
        },
        'synchronize_apps_no_cache': {
            'task': 'synchronize_apps_no_cache',
            'schedule': crontab(hour=4, minute=0),
            'args': ()
        },
        'load_google_suggestions' : {
            'task' : 'load_google_suggestions',
            'schedule' : crontab(hour='*/12', minute=0),
            'args' : ()
        },
        'load_deepl_suggestions' : {
            'task' : 'load_deepl_suggestions',
            'schedule' : crontab(hour='*/12', minute=0),
            'args' : ()
        },
        'load_microsoft_suggestions' : {
            'task' : 'load_microsoft_suggestions',
            'schedule' : crontab(hour='*/6', minute=0),
            'args' : ()
        },
        'update_check_urls_status' : {
            'task' : 'update_check_urls_status',
            'schedule' : crontab(hour='*/2', minute=0),
            'args' : ()
        },
    },

    task_routes = {
        #
        # The following are tasks that are probably non-blocking and can be run in parallel and are not critical
        #
        'load_google_suggestions': {
            'queue': NON_CRITICAL_INDEPENDENT_TASKS,
        },
        'load_deepl_suggestions': {
            'queue': NON_CRITICAL_INDEPENDENT_TASKS,
        },
        'load_microsoft_suggestions': {
            'queue': NON_CRITICAL_INDEPENDENT_TASKS,
        },

        #
        # The following are tasks which must be quick but still independent
        #
        'notify_changes' : {
            'queue': CRITICAL_INDEPENDENT_TASKS,
        },
        'notify_updates' : {
            'queue': CRITICAL_INDEPENDENT_TASKS,
        },
        'sync_mongodb_recent' : {
            'queue': CRITICAL_INDEPENDENT_TASKS,
        },
        'sync_repo_apps_cached': {
            'queue': CRITICAL_INDEPENDENT_TASKS,
        },
        'download_repository_single_app': {   # Only called from outside
            'queue': CRITICAL_INDEPENDENT_TASKS,
        },

        # The following are tasks which can be slow but still independent
        #
        'sync_mongodb_all' : {
            'queue': SLOW_INDEPENDENT_TASKS,
        },
        'sync_repo_apps_all': {
            'queue': SLOW_INDEPENDENT_TASKS,
        },
        'update_check_urls_status': {
            'queue': SLOW_INDEPENDENT_TASKS,
        },
        'download_repository_apps': {
            'queue': SLOW_INDEPENDENT_TASKS,
        },

        # The following are tasks which can only be run in a single queue
        'synchronize_apps_cache': {
            'queue': SINGLE_SYNC_TASKS,
        },
        'synchronize_apps_no_cache': {
            'queue': SINGLE_SYNC_TASKS,
        },
        'synchronize_single_app': {
            'queue': SINGLE_SYNC_TASKS,
        },
    }
)

@cel.task(name='notify_changes', bind=True)
def task_notify_changes(self):
    with my_app.app_context():
        return run_notifications()

@cel.task(name='notify_updates', bind=True)
def task_notify_updates(self):
    with my_app.app_context():
        return run_update_notifications()

@cel.task(name='synchronize_apps_cache', bind=True)
def synchronize_apps_cache_wrapper(self, source = None):
    if source is None:
        source = 'scheduled'

    with my_app.app_context():
        result = synchronize_apps_cache(source = source)
    task_sync_mongodb_recent.delay()
    return result

@cel.task(name='synchronize_apps_no_cache', bind=True)
def synchronize_apps_no_cache_wrapper(self, source = None):
    if source is None:
        source = 'scheduled'

    # synchronize all the apps
    with my_app.app_context():
        result = synchronize_apps_no_cache(source = source)

    # Call mongodb
    task_sync_mongodb_all.delay()
    return result

@cel.task(name='update_check_urls_status', bind=True)
def task_update_check_urls_status(self):
    with my_app.app_context():
        update_check_urls_status()

@cel.task(name='synchronize_single_app', bind=True)
def task_synchronize_single_app(self, source = None, single_app_url = None):
    if source is None:
        source = 'scheduled'

    with my_app.app_context():
        update_content_hash(single_app_url)
        result = synchronize_single_app_no_cached(source = source, single_app_url = single_app_url)

    task_sync_mongodb_recent.delay()
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

@cel.task(name='load_deepl_suggestions', bind=True)
def task_load_deepl_suggestions(self):
    with my_app.app_context():
        load_all_deepl_suggestions()

@cel.task(name='load_microsoft_suggestions', bind=True)
def task_load_microsoft_suggestions(self):
    with my_app.app_context():
        load_all_microsoft_suggestions()


@cel.task(name='sync_repo_apps_cached', bind=True)
def task_sync_repo_apps_cached(self):
    with my_app.app_context():
        changes = sync_repo_apps(force=False)
        if changes:
            task_download_repository_apps.delay("changes-in-repo")


@cel.task(name='sync_repo_apps_all', bind=True)
def task_sync_repo_apps_all(self):
    with my_app.app_context():
        changes = sync_repo_apps(force=True)
        if changes:
            task_download_repository_apps.delay("changes-in-repo")


@cel.task(name='download_repository_single_app', bind=True)
def task_download_repository_single_app(self, app_url):
    with my_app.app_context():
        changes = download_repository_single_app(app_url)
        if changes:
            task_sync_mongodb_recent.delay()

@cel.task(name='download_repository_apps', bind=True)
def task_download_repository_apps(self, source = None):
    if source is None:
        source = 'sched-down'

    with my_app.app_context():
        sync_id = start_synchronization(source=source, cached=False)

    try:
        with my_app.app_context():
            changes = download_repository_apps()
            if changes:
                synchronize_apps_cache_wrapper.delay()
    finally:
        with my_app.app_context():
            end_synchronization(sync_id, number = 0)
