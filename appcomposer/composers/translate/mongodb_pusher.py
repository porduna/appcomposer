
from celery import Celery
from celery.utils.log import get_task_logger
from pymongo import MongoClient
import datetime

import os
import unittest

# Fix the working directory when running from the script's own folder.
cwd = os.getcwd()
path = os.path.join("appcomposer", "composers", "translate")
if cwd.endswith(path):
    cwd = cwd[0:len(cwd)-len(path)]
    os.chdir(cwd)

from appcomposer import app as flask_app

cel = Celery('pusher_tasks', backend='amqp', broker='amqp://')
cel.conf.update(
    CELERYD_PREFETCH_MULTIPLIER="4",
    CELERYD_CONCURRENCY="8",
    CELERY_ACKS_LATE="1"
)

cli = MongoClient("mongodb://localhost")
db = cli.appcomposerdb
bundles = db.bundles

logger = get_task_logger(__name__)

@cel.task(name="push", bind=True, default_retry_delay=0)
def push(self, spec, lang, data, time):

    try:
        logger.info("[PUSH] Pushing to %s@%s on %s" % (lang, spec, time))

        bundle = {"spec": spec, "bundle": lang, "data": data, "time": time}
        cnt = bundles.find({"spec": spec, "bundle": lang}).count()
        logger.info("[PUSH]: Count: %d" % cnt)

        if cnt == 0:
            logger.info("[PUSH]: Inserting bundle")
            bundles.insert(bundle)
        else:
            logger.info("[PUSH]: Updating bundle... ")
            result = bundles.update({"spec": spec, "bundle": lang, "time": {"$lt": time}}, bundle)
            logger.info("[PUSH]: Update applied: %r" % result["updatedExisting"])
    except Exception as exc:

        logger.warn("[PUSH]: Exception occurred. Retrying soon.")
        raise self.retry(exc=exc, default_retry_delay=60, max_retries=None)


if __name__ == '__main__':
    # cel.worker_main(["worker"])
    push.apply(args=["es_ES_ALL", "app.xml", "ooo5", datetime.datetime.utcnow()-datetime.timedelta(minutes=1)])