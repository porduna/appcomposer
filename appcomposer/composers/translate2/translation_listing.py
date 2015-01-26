import requests
import random
import traceback

import appcomposer.db as db
from appcomposer.models import RepositoryApp

GOLAB_REPO = 'golabz'
EXTERNAL_REPO = 'external'

def download_golab_translations():
    try:
        apps = requests.get("http://www.golabz.eu/rest/apps/retrieve.json").json()
    except:
        traceback.print_exc()
        return

    apps_by_url = {}
    for app in apps:
        apps_by_url[app['url']] = app
    
    # 
    # This requires several steps.
    # 
    # Step 1: synchronize with the golabz repo
    ##########################################
    # 
    # Delete deprecated apps
    # 
    stored_apps = db.session.query(RepositoryApp).filter(repository=GOLAB_REPO).all()
    for stored_app in stored_apps:
        if stored_app.url not in apps_by_url:
            print stored_app.url, "not in the golabz repo anymore. Remove visibility?"
            # TODO

    # 
    # Add new apps
    # 
    for url in apps_by_url:
        pass
    



def retrieve_translations():
    existing_apps = requests.get("http://www.golabz.eu/rest/apps/retrieve.json").json()
    for app in existing_apps:
        app['original_languages'] = []
        app['original_languages_simplified'] = []
        app['translated_languages'] = {}
        app['translated_languages_simplified'] = {}

        if random.randint(0,1):
            app['original_languages'].append('es_ES_ALL')
            app['original_languages_simplified'].append('es')

        if random.randint(0,1):
            app['original_languages'].append('en_EN_ALL')
            app['original_languages_simplified'].append('en')

        if random.randint(0,1):
            app['original_languages'].append('de_DE_ALL')
            app['original_languages_simplified'].append('de')

        if len(app['original_languages']) == 0 or random.randint(0,1):
            app['original_languages'].append('fr_FR_ALL')
            app['original_languages_simplified'].append('fr')

        if random.randint(0,1):
            app['translated_languages']['es_ES_ALL'] = random.random()
            app['translated_languages_simplified']['es'] = app['translated_languages']['es_ES_ALL']

        if random.randint(0,1):
            app['translated_languages']['en_EN_ALL'] = random.random()
            app['translated_languages_simplified']['en'] = app['translated_languages']['en_EN_ALL']

        if len(app['translated_languages']) == 0 or random.randint(0,1):
            app['translated_languages']['fr_FR_ALL'] = random.random()
            app['translated_languages_simplified']['fr'] = app['translated_languages']['fr_FR_ALL']

    return existing_apps


