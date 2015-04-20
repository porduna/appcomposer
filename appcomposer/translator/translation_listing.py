import sys
import json
import datetime

import requests
from sqlalchemy.exc import SQLAlchemyError
from celery.utils.log import get_task_logger

from appcomposer.application import app
from appcomposer.db import db
from appcomposer.models import RepositoryApp, TranslatedApp
from appcomposer.translator.utils import get_cached_session, extract_metadata_information
from appcomposer.translator.ops import add_full_translation_to_app, retrieve_translations_percent, get_golab_default_user

GOLAB_REPO = u'golabz'
EXTERNAL_REPO = u'external'

DEBUG = True

logger = get_task_logger(__name__)

def synchronize_apps_cache():
    """Force obtaining the results and checking everything again to avoid inconsistences. 
    This can safely be run every few minutes, since most applications will be in the cache."""
    
    cached_requests = get_cached_session()
    synced_apps = _sync_golab_translations(cached_requests, force_reload = False)
    _sync_regular_apps(cached_requests, synced_apps, force_reload = False)
    
def synchronize_apps_no_cache():
    """Force obtaining the results and checking everything again to avoid inconsistences. This should be run once a day."""
    cached_requests = get_cached_session()
    synced_apps = _sync_golab_translations(cached_requests, force_reload = True)
    _sync_regular_apps(cached_requests, synced_apps, force_reload = True)

def _sync_golab_translations(cached_requests, force_reload):
    try:
        apps_response = cached_requests.get("http://www.golabz.eu/rest/apps/retrieve.json")
        apps_response.raise_for_status()
        apps = apps_response.json()
    except requests.RequestException:
        logger.warning("Error retrieving applications from golabz", exc_info = True)
        return

    apps_by_url = {}
    for app in apps:
        apps_by_url[app['app_url']] = app

    apps_by_id = {}
    for app in apps:
        apps_by_id[unicode(app['id'])] = app

    stored_apps = db.session.query(RepositoryApp).filter_by(repository=GOLAB_REPO).all()

    # 
    # Update or delete existing apps
    # 
    stored_ids = []
    for repo_app in stored_apps:
        external_id = unicode(repo_app.external_id)
        try:
            if external_id not in apps_by_id:
                # Delete old apps (translations are kept, and the app is kept, but not listed in the repository apps)
                db.session.delete(repo_app)
                db.session.commit()
            else:
                stored_ids.append(external_id)
                app = apps_by_id[external_id]
                _update_existing_app(cached_requests, repo_app, app_url = app['app_url'], title = app['title'], app_thumb = app['app_thumb'], description = app['description'], app_image = app['app_image'], app_link = app['app_golabz_page'], force_reload = force_reload)
        except SQLAlchemyError:
            # One error in one application shouldn't stop the process
            logger.warning("Error updating or deleting app %s" % app['app_url'], exc_info = True)
            continue

    #
    # Add new apps
    #
    for app in apps:
        if app['id'] not in stored_ids:
            try:
                _add_new_app(cached_requests, repository = GOLAB_REPO, 
                            app_url = app['app_url'], title = app['title'], external_id = app['id'],
                            app_thumb = app['app_thumb'], description = app['description'],
                            app_image = app['app_image'], app_link = app['app_golabz_page'],
                            force_reload = force_reload)
            except SQLAlchemyError:
                logger.warning("Error adding app %s" % app['app_url'], exc_info = True)
                continue

    return list(apps_by_url)

def _update_existing_app(cached_requests, repo_app, app_url, title, app_thumb, description, app_image, app_link, force_reload):
    if repo_app.name != title:
        repo_app.name = title
    if repo_app.app_thumb != app_thumb:
        repo_app.app_thumb = app_thumb
    if repo_app.description != description:
        repo_app.description = description
    if repo_app.app_link != app_link:
        repo_app.app_link = app_link
    if repo_app.app_image != app_image:
        repo_app.app_image = app_image

    _add_or_update_app(cached_requests, app_url, force_reload, repo_app)

def _add_new_app(cached_requests, repository, app_url, title, external_id, app_thumb, description, app_image, app_link, force_reload):
    repo_app = RepositoryApp(name = title, url = app_url, external_id = external_id, repository = repository)
    repo_app.app_thumb = app_thumb
    repo_app.description = description
    repo_app.app_link = app_link
    repo_app.app_image = app_image
    db.session.add(repo_app)

    _add_or_update_app(cached_requests, app_url, force_reload, repo_app)

def _sync_regular_apps(cached_requests, already_synchronized_app_urls, force_reload):
    app_urls = db.session.query(TranslatedApp.url).all()
    for app_url, in app_urls:
        if app_url not in already_synchronized_app_urls:
            _add_or_update_app(cached_requests, app_url, force_reload, repo_app = None)


def _add_or_update_app(cached_requests, app_url, force_reload, repo_app = None):
    now = datetime.datetime.now()

    if DEBUG:
        logger.debug("Starting %s" % app_url)

    failing = False
    try:
        metadata_information = extract_metadata_information(app_url, cached_requests, force_reload)
        if app_url == 'http://www.weblab.deusto.es/pub/i18n_tests/i18n.xml':
            logger.error(metadata_information)
    except Exception:
        logger.warning("Error extracting information from %s" % app_url, exc_info = True)
        metadata_information = {}
        failing = True

    if repo_app is not None:
        repo_app.translatable = metadata_information.get('translatable', False)
        repo_app.adaptable = metadata_information.get('adaptable', False)
        repo_app.original_translations = u','.join(metadata_information.get('original_translations', {}).keys())
        repo_app.last_change = now
        repo_app.last_check = now

        if failing:
            repo_app.failing = True
            repo_app.failing_since = now

    default_user = get_golab_default_user()

    if metadata_information.get('translatable'):
        translation_url = metadata_information.get('default_translation_url')
        original_messages = metadata_information['default_translations']
        for language, translated_messages in metadata_information['original_translations'].iteritems():
            add_full_translation_to_app(user = default_user, app_url = app_url, translation_url = translation_url, 
                                language = language, target = u'ALL', translated_messages = translated_messages, 
                                original_messages = original_messages, from_developer = True)

        translation_percent = retrieve_translations_percent(translation_url, original_messages)
        if repo_app is not None:
            repo_app.translation_percent = json.dumps(translation_percent)
    
    db.session.commit()
    
if __name__ == '__main__':
    from appcomposer import app as my_app
    with my_app.app_context():
        synchronize_apps_cache()
