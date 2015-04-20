import os
import sys
import json
import datetime
from celery.schedules import crontab
from celery.utils.log import get_task_logger

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

cel = Celery('pusher_tasks', backend='amqp', broker='amqp://')

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
    }
)


from appcomposer import app as my_app
from appcomposer.translator.translation_listing import synchronize_apps_cache, synchronize_apps_no_cache
from appcomposer.translator.mongodb_pusher import push, sync

@cel.task(name='synchronize_apps_cache', bind=True)
def synchronize_apps_cache_wrapper(self):
    with my_app.app_context():
        result = synchronize_apps_cache()
    sync(self)
    return result

@cel.task(name='synchronize_apps_no_cache', bind=True)
def synchronize_apps_no_cache_wrapper(self):
    with my_app.app_context():
        result = synchronize_apps_no_cache()
    sync(self)
    return result

@cel.task(name="push", bind=True)
def push_task(self, translation_url, lang, target):
    return push(self, translation_url, lang, target)

@cel.task(name="sync", bind=True)
def sync_wrapper(self):
    return sync(self)

