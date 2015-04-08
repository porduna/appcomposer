from datetime import timedelta, datetime
import json
import os

from celery import Celery
from celery.utils.log import get_task_logger
from bson import json_util
from pymongo import MongoClient

# Fix the working directory when running from the script's own folder.
from pymongo.errors import DuplicateKeyError
import sys

cwd = os.getcwd()
path = os.path.join("appcomposer", "composers", "translate")
if cwd.endswith(path):
    cwd = cwd[0:len(cwd) - len(path)]
    os.chdir(cwd)

sys.path.insert(0, cwd)


from appcomposer.application import app as flask_app

# Fix the path so it can be run more easily, etc.
from appcomposer.composers.translate.bundles import BundleManager
from appcomposer.composers.translate.db_helpers import _db_get_diff_specs, _db_get_ownerships, load_appdata_from_db


MONGODB_SYNC_PERIOD = flask_app.config.get("MONGODB_SYNC_PERIOD", 60*15)  # Every 15 min by default.

cel = Celery('pusher_tasks', backend='amqp', broker='amqp://')
cel.conf.update(
    CELERYD_PREFETCH_MULTIPLIER="4",
    CELERYD_CONCURRENCY="8",
    CELERY_ACKS_LATE="1",
    CELERY_IGNORE_RESULT=True,

    CELERYBEAT_SCHEDULE = {
        'sync-periodically': {
            'task': 'sync',
            'schedule': timedelta(seconds=MONGODB_SYNC_PERIOD),
            'args': ()
        }
    }
)

mongo_client = MongoClient(flask_app.config["MONGODB_PUSHES_URI"])
mongo_db = mongo_client.appcomposerdb
mongo_bundles = mongo_db.bundles

logger = get_task_logger(__name__)

def retrieve_mongodb_contents():
    results = [ result for result in mongo_bundles.find() ]
    serialized = json.dumps(results, default=json_util.default)
    return { 'bundles' : json.loads(serialized) }

@cel.task(name="push", bind=True)
def push(self, spec, lang, data, time):
    """
    Pushes a Bundle into the MongoDB.
    @param spec: Spec to which the Bundle belongs.
    @param lang: Full bundle identifier, in the ca_ES_ALL format.
    @param data: Contents of the Bundle.
    @param time: Time the Bundle was last modified. If the proposed change to push
    is actually older from the one in the dabatase, nothing will be updated.
    """
    try:
        logger.info("[PUSH] Pushing to %s@%s on %s" % (lang, spec, time))

        bundle_id = lang + "::" + spec
        bundle = {"_id": bundle_id, "spec": spec, "bundle": lang, "data": data, "time": time}

        try:
            mongo_bundles.update({"_id": bundle_id, "time": {"$lt": time}},
                           bundle,
                           upsert=True)
            logger.info("[PUSH]: Updated bundle %s" % bundle_id)
        except DuplicateKeyError:
            logger.info("[PUSH]: Ignoring push for %s (newer date exists already)" % bundle_id)

    except Exception as exc:

        logger.warn("[PUSH]: Exception occurred. Retrying soon.")
        raise self.retry(exc=exc, default_retry_delay=60, max_retries=None)


@cel.task(name="sync", bind=True)
def sync(self):
    """
    Fully synchronizes the local database leading translations with
    the MongoDB.
    """
    logger.info("[SYNC]: Starting Sync task")

    # Apparently the context is required to access the local DB
    # cleanly through Flask-SQLAlchemy. Maybe eventually this task
    # should use SQLAlchemy on its own.
    with flask_app.app_context():

        # Remember the time in which we start this process. This is so that
        # later we can avoid deleting bundles that were created in this time
        # but which were not present on the _db_get_diff_specs() call yet.
        # (That is, to avoid a concurrency issue that could occur when creating
        # new translations).
        start_time = datetime.utcnow()

        # Retrieve a list of specs that are currently hosted in the local DB.
        specs = _db_get_diff_specs()

        # Store a list of bundleids
        bundleids = []

        for spec in specs:
            # For each spec we get the ownerships.
            ownerships = _db_get_ownerships(spec)

            for ownership in ownerships:
                lang = ownership.value
                full_app_data = load_appdata_from_db(ownership.app)
                bm = BundleManager.create_from_existing_app(full_app_data)

                # Get a list of fullcodes (including the group).
                keys = [key for key in bm._bundles.keys() if BundleManager.fullcode_to_partialcode(key) == lang]

                # TODO: The graining of the modification date will actually lead
                # to unneeded updates.
                update_date = ownership.app.modification_date

                for full_lang in keys:

                    # Create the MongoDB id.
                    bundleid = full_lang + "::" + spec
                    bundleids.append(bundleid)

                    logger.info("[SYNC]: Considering synchronization of: %s" % bundleid)

                    # Launch a task to carry out the synchronization if needed.
                    # The current method will waste some bandwidth but require
                    # a single query per bundle.
                    data = json.dumps(bm.get_bundle(full_lang).get_msgs())
                    push.delay(spec, full_lang, data, update_date)


        # Now that the bundles that are actually in the local DB have been
        # supposedly synchronized, it's time to delete the ones that no longer exist.
        # We avoid deleting those which were created while we executed this synchronization
        # method, because a new app could have been created in the meantime and could be deleted
        # if we did.
        mongo_bundles.remove({"_id": {"$nin": bundleids}, "time": {"$lt": start_time}})

        logger.info("[SYNC]: Sync finished.")

if __name__ == '__main__':
    cel.worker_main(sys.argv)
