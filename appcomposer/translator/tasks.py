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

# cel = Celery('pusher_tasks', backend='amqp', broker='amqp://')
cel = Celery('pusher_tasks', backend='redis', broker='redis://localhost:6379/6')

cel.conf.update(
    CELERYD_PREFETCH_MULTIPLIER="4",
    CELERYD_CONCURRENCY="8",
    CELERY_ACKS_LATE="1",
    CELERY_IGNORE_RESULT=True,

    CELERYBEAT_SCHEDULE = {
        'synchronize_apps_cache': {
            'task': 'synchronize_apps_cache',
            'schedule': datetime.timedelta(minutes=5),
            'args': ()
        },
        'synchronize_apps_no_cache': {
            'task': 'synchronize_apps_no_cache',
            'schedule': crontab(hour=3, minute=0),
            'args': ()
        },
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
    }
)


from appcomposer import app as my_app, db
from appcomposer.models import TranslationCurrentActiveUser
from appcomposer.translator.translation_listing import synchronize_apps_cache, synchronize_apps_no_cache, load_all_google_suggestions
from appcomposer.translator.mongodb_pusher import sync
from appcomposer.translator.notifications import run_notifications

@cel.task(name='notify_changes', bind=True)
def notify_changes(self):
    with my_app.app_context():
        return run_notifications()

@cel.task(name='synchronize_apps_cache', bind=True)
def synchronize_apps_cache_wrapper(self, source = None, single_app_url = None):
    if source is None:
        source = 'scheduled'

    with my_app.app_context():
        result = synchronize_apps_cache(source = source, single_app_url = single_app_url)
    sync(self, True)
    return result

@cel.task(name='synchronize_apps_no_cache', bind=True)
def synchronize_apps_no_cache_wrapper(self, source = None, single_app_url = None, must_sync = True):
    if source is None:
        source = 'scheduled'
    with my_app.app_context():
        result = synchronize_apps_no_cache(source = source, single_app_url = single_app_url)
    if must_sync:
        sync(self, False)
    return result

@cel.task(name="sync", bind=True)
def sync_wrapper(self):
    return sync(self, True)

@cel.task(name="sync_no_cache", bind=True)
def sync_no_cache_wrapper(self):
    return sync(self, False)

@cel.task(name='load_google_suggestions', bind=True)
def load_google_suggestions(self):
    with my_app.app_context():
        load_all_google_suggestions()

@cel.task(name='delete_old_realtime_active_users', bind=True)
def delete_old_realtime_active_users(self):
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
