import json
from flask import Blueprint, jsonify, render_template

from appcomposer.translator.mongodb_pusher import retrieve_mongodb_app, retrieve_mongodb_translation_url
    
translations_blueprint_v1 = Blueprint('translations', __name__)

@translations_blueprint_v1.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

def _get_data(lang, url):
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
