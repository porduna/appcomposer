from datetime import timedelta, datetime
import json
import os

from celery import Celery
from celery.utils.log import get_task_logger
from bson import json_util
from pymongo import MongoClient
from sqlalchemy.orm import joinedload

# Fix the working directory when running from the script's own folder.
from pymongo.errors import DuplicateKeyError

from appcomposer.db import db
from appcomposer.application import app as flask_app
from appcomposer.models import TranslationUrl, TranslationBundle, ActiveTranslationMessage

logger = get_task_logger(__name__)

MONGODB_SYNC_PERIOD = flask_app.config.get("MONGODB_SYNC_PERIOD", 60*10)  # Every 10 min by default.

if flask_app.config["ACTIVATE_TRANSLATOR_MONGODB_PUSHES"]:
    mongo_client = MongoClient(flask_app.config["MONGODB_PUSHES_URI"])
    mongo_db = mongo_client.appcomposerdb
    mongo_bundles = mongo_db.bundles
    mongo_translation_urls = mongo_db.translation_urls
else:
    print "Warning: MONGODB is not activated. Use ACTIVATE_TRANSLATOR_MONGODB_PUSHES"

def retrieve_mongodb_contents():
    bundles_results = [ result for result in mongo_bundles.find() ]
    bundles_serialized = json.dumps(bundles_results, default=json_util.default)

    translations_url_results = [ result for result in mongo_translation_urls.find() ]
    translations_url_serialized = json.dumps(translations_url_results, default=json_util.default)

    return { 'bundles' : json.loads(bundles_serialized), 'translation_urls' : json.loads(translations_url_serialized) }

def push(self, translation_url, lang, target):
    if not flask_app.config["ACTIVATE_TRANSLATOR_MONGODB_PUSHES"]:
        return

    try:
        logger.info("[PUSH] Pushing to %s@%s" % (lang, translation_url))
        print("[PUSH] Pushing to %s@%s" % (lang, translation_url))

        with flask_app.app_context():
            translation_bundle = db.session.query(TranslationBundle).filter(TranslationBundle.translation_url_id == TranslationUrl.id, TranslationUrl.url == translation_url, TranslationBundle.language == lang, TranslationBundle.target == target).options(joinedload("translation_url")).first()
            if translation_bundle is None:
                return
            payload = {}
            max_date = datetime(1970, 1, 1)
            for message in translation_bundle.active_messages:
                payload[message.key] = message.value
                if message.datetime > max_date:
                    max_date = message.datetime
            data = json.dumps(payload)

            lang_pack = lang + '_' + target

            bundle_id = lang_pack + '::' + translation_url
            bundle = { '_id' : bundle_id, 'url' : translation_url,  'bundle' : lang_pack, 'data' : data, 'time' : max_date }
            try:
                mongo_translation_urls.update({'_id' : bundle_id, 'time' : { '$lt' : max_date }}, bundle, upsert = True)
                logger.info("[PUSH]: Updated translation URL bundle %s" % bundle_id)
                print("[PUSH]: Updated translation URL bundle %s" % bundle_id)
            except DuplicateKeyError:
                print("[PUSH]: Ignoring push for translation URL bundle %s (newer date exists already)" % bundle_id)
            
            app_bundle_ids = []
            for application in translation_bundle.translation_url.apps:
                app_bundle_id = lang_pack + '::' + application.url
                app_bundle_ids.append(app_bundle_id)
                bundle = { '_id' : app_bundle_id, 'spec' : application.url,  'bundle' : lang_pack, 'data' : data, 'time' : max_date }
                try:
                    mongo_bundles.update({'_id' : app_bundle_id, 'time' : { '$lt' : max_date }}, bundle, upsert = True)
                    logger.info("[PUSH]: Updated application bundle %s" % app_bundle_id)
                    print("[PUSH]: Updated application bundle %s" % app_bundle_id)
                except DuplicateKeyError:
                    print("[PUSH]: Ignoring push for application bundle %s (newer date exists already)" % app_bundle_id)

            return bundle_id, app_bundle_ids
    except Exception as exc:
        logger.warn("[PUSH]: Exception occurred. Retrying soon.", exc_info = True)
        print("[PUSH]: Exception occurred. Retrying soon.")
        if self is not None:
            raise self.retry(exc=exc, default_retry_delay=60, max_retries=None)

def sync(self, only_recent):
    """
    Fully synchronizes the local database leading translations with
    the MongoDB.
    """
    if not flask_app.config["ACTIVATE_TRANSLATOR_MONGODB_PUSHES"]:
        return

    logger.info("[SYNC]: Starting Sync task")

    start_time = datetime.utcnow()

    if only_recent:
        oldest = datetime.utcnow() - timedelta(hours=1)
    else:
        oldest = datetime(1970, 1, 1)

    with flask_app.app_context():
        translation_bundles = [ {
                'translation_url' : bundle.translation_url.url,
                'language' : bundle.language,
                'target' : bundle.target
            } for bundle in db.session.query(TranslationBundle).filter(ActiveTranslationMessage.datetime >= oldest, ActiveTranslationMessage.bundle_id == TranslationBundle.id).group_by(TranslationBundle.id).options(joinedload("translation_url")).all() ]
    
    all_translation_url_ids = []
    all_app_ids = []

    for translation_bundle in translation_bundles:
        response = push(self = None, translation_url = translation_bundle['translation_url'], lang = translation_bundle['language'], target = translation_bundle['target'])
        if response is None:
            logger.warn("Pushing translation for %s of %s returned None" % (translation_bundle['translation_url'], translation_bundle['language']))
            continue
        translation_url_id, app_ids = response
        all_translation_url_ids.append(translation_url_id)
        all_app_ids.extend(app_ids)
    
    mongo_bundles.remove({"_id": {"$nin": all_app_ids}, "time": {"$lt": start_time}})
    mongo_translation_urls.remove({"_id": {"$nin": all_translation_url_ids}, "time": {"$lt": start_time}})

    logger.info("[SYNC]: Sync finished.")

