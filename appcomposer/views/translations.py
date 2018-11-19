import json
from flask import Blueprint, jsonify, render_template

from appcomposer.db import db
from appcomposer.models import TranslationUrl, TranslatedApp, TranslationBundle, ActiveTranslationMessage
from appcomposer.translator.mongodb_pusher import retrieve_mongodb_app, retrieve_mongodb_translation_url
    
translations_blueprint_v1 = Blueprint('translations', __name__)

@translations_blueprint_v1.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

def _get_list(url):
    translation_url = db.session.query(TranslationUrl).filter_by(url=url).first()
    if translation_url is None:
        translated_app = db.session.query(TranslatedApp).filter_by(url=url).first()
        if translated_app is None:
            return None
        
        translation_url = translated_app.translation_url
        if translation_url is None:
            return None

    bundles = db.session.query(TranslationBundle).filter_by(translation_url=translation_url, target='ALL').first()

    languages = []
    for bundle in bundles:
        languages.append(bundle.language)
    return languages

def _get_data(lang, url):
    translation_url = db.session.query(TranslationUrl).filter_by(url=url).first()
    if translation_url is None:
        translated_app = db.session.query(TranslatedApp).filter_by(url=url).first()
        if translated_app is None:
            return None
        
        translation_url = translated_app.translation_url
        if translation_url is None:
            return None

    if '_' in lang:
        generic = lang.split('_')[0] + '_ALL'
        specific = lang
    else:
        generic = specific = lang + '_ALL'

    bundle = db.session.query(TranslationBundle).filter_by(translation_url=translation_url, target='ALL', language=specific).first()
    if bundle is None and generic != specific:
        bundle = db.session.query(TranslationBundle).filter_by(translation_url=translation_url, target='ALL', language=generic).first()

    if bundle is None:
        return None

    data = {}
    for message in db.session.query(ActiveTranslationMessage).filter_by(bundle=bundle).all():
        data[message.key] = message.value
    
    return json.dumps(data)

    # This is using MongoDB, which is slower in production
    if '_' not in lang:
        lang = '{}_ALL'.format(lang)
    data = retrieve_mongodb_app(lang, target='ALL', url=url)
    if data is None:
        data = retrieve_mongodb_translation_url(lang, target='ALL', url=url)
    if data is None:
        new_lang = lang.split('_')[0] + '_ALL'
        if new_lang != lang:
            return _get_data(new_lang, url)

    return data

@translations_blueprint_v1.route('/languages/<path:url>')
def get_language_list(url):
    languages = _get_list(url)
    return jsonify(languages=languages), 404

@translations_blueprint_v1.route('/<lang>/<path:url>')
def get_translations(lang, url):
    data = _get_data(lang, url)
    if data is None:
        return jsonify()

    return jsonify(json.loads(data))

@translations_blueprint_v1.route('/by-key/<lang>/<path:url>')
def get_translations_by_key(lang, url):
    data = _get_data(lang, url)
    if data is None:
        return jsonify()

    return jsonify(json.loads(data))

@translations_blueprint_v1.route('/list/<lang>/<path:url>')
def get_translations_by_list(lang, url):
    data = _get_data(lang, url)
    if data is None:
        return jsonify([])

    messages = [ {
            'key': key,
            'value': value,
        } for key, value in json.loads(data).items() ]

    return jsonify(messages)

@translations_blueprint_v1.route('/tests/test1.html')
def test1_html():
    return render_template('test-translations-v1-1.html')

@translations_blueprint_v1.route('/tests/test2.html')
def test2_html():
    return render_template('test-translations-v1-2.html')
