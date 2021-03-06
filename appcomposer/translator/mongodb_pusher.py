from datetime import timedelta, datetime
import json

from celery.utils.log import get_task_logger
from bson import json_util
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from sqlalchemy.orm import joinedload

# Fix the working directory when running from the script's own folder.
from pymongo.errors import DuplicateKeyError

from appcomposer.db import db
from appcomposer.application import app as flask_app
from appcomposer.models import TranslationUrl, TranslationBundle, ActiveTranslationMessage

logger = get_task_logger(__name__)

MONGODB_SYNC_PERIOD = flask_app.config.get("MONGODB_SYNC_PERIOD", 60*10)  # Every 10 min by default.

if flask_app.config["ACTIVATE_TRANSLATOR_MONGODB_PUSHES"]:
    mongodb_uris = []
    if flask_app.config.get("MONGODB_PUSHES_URIS"):
        mongodb_uris = list(flask_app.config["MONGODB_PUSHES_URIS"])
    if flask_app.config.get("MONGODB_PUSHES_URI"):
        if flask_app.config["MONGODB_PUSHES_URI"] not in mongodb_uris:
            mongodb_uris.append(flask_app.config["MONGODB_PUSHES_URI"])

    all_mongo_bundles = []
    all_mongo_translation_urls = []

    for mongodb_uri in mongodb_uris:
        mongo_client = MongoClient(mongodb_uri)
        mongo_db = mongo_client.appcomposerdb
        current_mongo_bundles = mongo_db.bundles
        current_mongo_translation_urls = mongo_db.translation_urls
        
        all_mongo_bundles.append(current_mongo_bundles)
        all_mongo_translation_urls.append(current_mongo_translation_urls)
else:
    print "Warning: MONGODB is not activated. Use ACTIVATE_TRANSLATOR_MONGODB_PUSHES"

def retrieve_mongodb_contents():
    bundles_results = [ result for result in all_mongo_bundles[0].find() ]
    bundles_serialized = json.dumps(bundles_results, default=json_util.default)

    translations_url_results = [ result for result in all_mongo_translation_urls[0].find() ]
    translations_url_serialized = json.dumps(translations_url_results, default=json_util.default)

    return { 'bundles' : json.loads(bundles_serialized), 'translation_urls' : json.loads(translations_url_serialized) }

def retrieve_mongodb_apps():
    apps = {}
    for app in all_mongo_bundles[0].find({}, {'spec':True, 'bundle':True}):
        url = app['spec']
        bundle = app['bundle']
        lang, target = bundle.rsplit('_', 1)
        if url not in apps:
            apps[url] = []

        apps[url].append({
            'target' : target,
            'lang' : lang
        })

    return apps

def retrieve_mongodb_app(lang, target, url):
    identifier = "{0}_{1}::{2}".format(lang, target, url)
    result = all_mongo_bundles[0].find_one({ '_id': identifier })
    if result is not None:
        return result['data']
    return None

def retrieve_mongodb_translation_url(lang, target, url):
    identifier = "{0}_{1}::{2}".format(lang, target, url)
    result = all_mongo_translation_urls[0].find_one({ '_id': identifier })
    if result is not None:
        return result['data']
    return None

def retrieve_mongodb_urls():
    apps = {}
    for app in all_mongo_translation_urls[0].find({}, {'url':True, 'bundle':True}):
        url = app['url']
        bundle = app['bundle']
        lang, target = bundle.rsplit('_', 1)
        if url not in apps:
            apps[url] = []

        apps[url].append({
            'target' : target,
            'lang' : lang
        })
    return apps


def push(self, translation_url, lang, target, recursive = False):
    if not flask_app.config["ACTIVATE_TRANSLATOR_MONGODB_PUSHES"]:
        return

    if lang.startswith('en_'):
        # Don't send any English text
        return

    previous = []

    if not recursive:
        if lang == 'zh_CN':
            for record in push(self, translation_url, 'zh_ALL', target, recursive=True):
                previous.append(record)
        elif lang == 'zh_ALL':
            for record in push(self, translation_url, 'zh_CN', target, recursive=True):
                previous.append(record)

    try:
        logger.info("[PUSH] Pushing to %s@%s" % (lang, translation_url))
        print("[PUSH] Pushing to %s@%s" % (lang, translation_url))

        with flask_app.app_context():
            translation_bundle = db.session.query(TranslationBundle).filter(TranslationBundle.translation_url_id == TranslationUrl.id, TranslationUrl.url == translation_url, TranslationBundle.language == lang, TranslationBundle.target == target).options(joinedload("translation_url")).first()
            if translation_bundle is None:
                if lang == 'zh_CN':
                    translation_bundle = db.session.query(TranslationBundle).filter(TranslationBundle.translation_url_id == TranslationUrl.id, TranslationUrl.url == translation_url, TranslationBundle.language == 'zh_ALL', TranslationBundle.target == target).options(joinedload("translation_url")).first()
                elif lang == 'zh_ALL':
                    translation_bundle = db.session.query(TranslationBundle).filter(TranslationBundle.translation_url_id == TranslationUrl.id, TranslationUrl.url == translation_url, TranslationBundle.language == 'zh_CN', TranslationBundle.target == target).options(joinedload("translation_url")).first()

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
            for mongo_translation_urls in all_mongo_translation_urls:
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
                for mongo_bundles in all_mongo_bundles:
                    try:
                        mongo_bundles.update({'_id' : app_bundle_id, 'time' : { '$lt' : max_date }}, bundle, upsert = True)
                        logger.info("[PUSH]: Updated application bundle %s" % app_bundle_id)
                        print("[PUSH]: Updated application bundle %s" % app_bundle_id)
                    except DuplicateKeyError:
                        print("[PUSH]: Ignoring push for application bundle %s (newer date exists already)" % app_bundle_id)
            
            previous.append([bundle_id, app_bundle_ids])
            return previous
    except ServerSelectionTimeoutError as exc:
        logger.warn("[PUSH]: Exception occurred due to server disconnect. NOT RETRYING.", exc_info = True)
        return 'timeout'
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
        oldest = datetime.utcnow() - timedelta(minutes=30)
    else:
        oldest = datetime(1970, 1, 1)

    with flask_app.app_context():
        translation_bundles = [ {
                'translation_url' : bundle.translation_url.url,
                'language' : bundle.language,
                'target' : bundle.target
            } for bundle in db.session.query(TranslationBundle).filter(ActiveTranslationMessage.datetime >= oldest, ActiveTranslationMessage.bundle_id == TranslationBundle.id).group_by(TranslationBundle.id).options(joinedload("translation_url")).all() ]
    
    if translation_bundles:
        all_translation_url_ids = []
        all_app_ids = []

        for translation_bundle in translation_bundles:
            responses = push(self = None, translation_url = translation_bundle['translation_url'], lang = translation_bundle['language'], target = translation_bundle['target'])
            if responses is None:
                logger.warn("Pushing translation for %s of %s returned None" % (translation_bundle['translation_url'], translation_bundle['language']))
                continue

            if responses == 'timeout':
                logger.warn("Pushing translation for %s of %s returned a timeout error" % (translation_bundle['translation_url'], translation_bundle['language']))
                break

            for response in responses:
                translation_url_id, app_ids = response
                all_translation_url_ids.append(translation_url_id)
                all_app_ids.extend(app_ids)
        
        if not only_recent:
            for mongo_bundles in all_mongo_bundles:
                mongo_bundles.remove({"_id": {"$nin": all_app_ids}, "time": {"$lt": start_time}})
            
            for mongo_translation_urls in all_mongo_translation_urls:
                mongo_translation_urls.remove({"_id": {"$nin": all_translation_url_ids}, "time": {"$lt": start_time}})

    logger.info("[SYNC]: Sync finished.")

def sync_mongodb_all(self):
    return sync(self, only_recent = False)

def sync_mongodb_last_hour(self):
    return sync(self, only_recent = True)




