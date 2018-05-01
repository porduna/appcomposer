import json
import traceback
from functools import wraps

from collections import OrderedDict

from flask import Blueprint, make_response, request, url_for, jsonify, current_app
from flask_cors import cross_origin

from appcomposer.db import db
from appcomposer.models import RepositoryApp
from appcomposer.login import requires_golab_api_login, current_golab_user
from appcomposer.exceptions import TranslatorError
from appcomposer.languages import obtain_groups, obtain_languages, get_locale_english_name
from appcomposer.utils import public
from appcomposer.translator.extractors import extract_local_translations_url
from appcomposer.translator.ops import add_full_translation_to_app, retrieve_stored, retrieve_suggestions, retrieve_translations_stats, register_app_url, update_user_status, get_user_status

from appcomposer.languages import guess_default_language

import flask_cors.core as cors_core
cors_core.debugLog = lambda *args, **kwargs : None


translator_api_blueprint = Blueprint('translator_api', __name__, static_folder = '../../translator3/dist/', static_url_path = '/web')


def api(func):
    """If a method is annotated with api, we will check regular errors and wrap them to a JSON document"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TranslatorError as e:
            if e.code == 500:
                current_app.logger.error("Error processing request: %s" % e, exc_info = True)
                print("Error processing request: %s" % e)
            traceback.print_exc()
            return make_response(json.dumps({ 'result' : 'error', 'message' : e.args[0] }), e.code)
        except Exception as e:
            current_app.logger.error("Unknown error processing request: %s" % e, exc_info = True)
            print("Unknown error processing request: %s" % e)
            traceback.print_exc()
            return make_response(json.dumps({ 'result' : 'error', 'message' : e.args[0] }), 500)
    return wrapper

@translator_api_blueprint.route("/user/authenticate")
@public
@cross_origin()
@api
def check_authn():
    cur_url = request.values.get("cur_url")
    golab_user = current_golab_user()
    if golab_user:
        return jsonify(**{ "result" : "ok", "display_name" : golab_user.display_name })
    else:
        return jsonify(**{ "result" : "fail", "redirect" : url_for('graasp_oauth_login', next = cur_url, _external = True) })

@translator_api_blueprint.route("/user/default_language")
@public
@cross_origin()
@api
def guess_default_language_view():
    return jsonify(language = guess_default_language())

@translator_api_blueprint.route('/apps/repository')
@public
@cross_origin()
@api
def api_translations():
    all_applications = []  # With categories
    applications = []
    laboratories = []
    others = []

    # Add categories
    apps_category = {
        "id": "apps",
        "category": "Apps",
        "items": applications
    }
    labs_category = {
        "id": "labs",
        "category": "Labs",
        "items": laboratories
    }
    others_category = {
        "id": "others",
        "category": "Others",
        "items": others
    }

    all_applications.append(apps_category)
    all_applications.append(labs_category)
    all_applications.append(others_category)

    for repo_app in db.session.query(RepositoryApp).filter_by(translatable = True).all():
        original_languages = repo_app.original_translations.split(',')
        if original_languages == "":
            original_languages = []
        original_languages_simplified = [ lang.split('_')[0] for lang in original_languages ]
        try:
            translated_languages = json.loads(repo_app.translation_percent or '{}') or {}
        except ValueError:
            translated_languages = {}

        # translation_percent sometimes have something like "nl_ALL_ALL" and sometimes "nl_ALL_13-18". We should 
        # always take the one of _ALL
        keys_to_remove = []
        for lang_key in translated_languages:
            if not lang_key.endswith("_ALL") and (lang_key.rsplit('_', 1)[0] + '_ALL') in translated_languages:
                keys_to_remove.append(lang_key)

        for key in keys_to_remove:
            translated_languages.pop(key, None)

        languages = {}
        for translated_lang, progress in translated_languages.iteritems():
            translated_lang_pack = translated_lang.split('_')
            if translated_lang_pack[1] == 'ALL':
                translated_lang_simplified = translated_lang.split('_')[0]
                if translated_lang_simplified == 'zh':
                    translated_lang_simplified = 'zh_CN'
            else:
                translated_lang_simplified = translated_lang_pack[0] + '_' + translated_lang_pack[1]
            
            translated_lang_country = '_'.join(translated_lang.split('_')[:2])
            name = get_locale_english_name(*translated_lang_country.split('_'))
            languages[translated_lang_country] = {
                'original' : translated_lang_country in original_languages,
                'progress' : progress,
                # 'name': translated_lang_simplified,
                'name': name,
            }

        languages_obj = []

        for lang_key, lang_value in languages.iteritems():
            languages_obj.append({
                'name': lang_value['name'],
                'original': lang_value['original'],
                'progress': lang_value['progress'],
                'key': lang_key,
            })

        # TODO: add Graasp and so on, plus use the retrieval method (e.g., labs/retrieve.json vs. apps/retrieve.json) to know whether it's one thing or the other
        app_link = repo_app.app_link or ''
        if repo_app.repository == 'golabz' and (app_link.startswith('https://www.golabz.eu/app/') or app_link.startswith('https://www.golabz.eu/apps/') or app_link.startswith('https://www.golabz.eu/content/')):
            where = applications
        elif repo_app.repository == 'golabz' and (app_link.startswith('https://www.golabz.eu/lab/') or app_link.startswith('https://www.golabz.eu/labs/')):
            where = laboratories
        else:
            where = others

        where.append({
            'original_languages' : original_languages,
            'original_languages_simplified' : original_languages_simplified,
            'translated_languages' : translated_languages,
            'languages' : languages,
            'languages_obj' : languages_obj,
            'source' : repo_app.repository,
            'id' : repo_app.external_id,
            'description': repo_app.description,
            'app_url' : repo_app.url,
            'app_thumb' : repo_app.app_thumb,
            'app_link' : repo_app.app_link,
            'app_image' : repo_app.app_image,
            'title' : repo_app.name,
        })

    resp = make_response(json.dumps(all_applications))
    resp.content_type = 'application/json'
    return resp



@translator_api_blueprint.route('/info/languages')
@public
@cross_origin()
@api
def api_languages():
    ordered_dict = OrderedDict()
    languages = list(obtain_languages().iteritems())
    languages.sort(lambda x1, x2 : cmp(x1[1], x2[1]))
    for lang_code, lang_name in languages:
        ordered_dict[lang_code] = lang_name
    resp = make_response(json.dumps(ordered_dict, indent = 4))
    resp.content_type = 'application/json'
    return resp

@translator_api_blueprint.route('/info/languages_default')
@public
@cross_origin()
@api
def api_languages_default():
    languages = list(obtain_languages().iteritems())
    languages.sort(lambda x1, x2 : cmp(x1[1], x2[1]))
    list_of_languages = []
    for lang_code, lang_name in languages:
        if lang_code.startswith('all'):
            continue
        list_of_languages.append({
            'name': lang_name,
            'code': lang_code.split('_')[0]
        })
    contents = {
        'default': (guess_default_language() or 'en').split('_')[0],
        'languages': list_of_languages,
    }
    resp = make_response(json.dumps(contents, indent = 4))
    resp.content_type = 'application/json'
    return resp


@translator_api_blueprint.route('/info/groups')
@public
@cross_origin()
@api
def api_groups():
    return jsonify(**obtain_groups())

@translator_api_blueprint.route("/apps/bundles/<language>/<target>/checkModifications", methods=["GET"])
@requires_golab_api_login
@cross_origin()
@api
def check_modifications(language, target):
    """
    Retrieves the last modification date and the active users.
    """
    app_url = request.values.get('app_url')

    update_user_status(language = language, target = target, app_url = app_url, user = current_golab_user())
    data = get_user_status(language = language, target = target, app_url = app_url, user = current_golab_user())
    
#     data = {
#         "modificationDate": "2015-07-07T23:20:08Z",
#         "modificationDateByOther": "2015-07-07T23:20:08Z",
#         "time_now": "2015/12/01T20:83:23Z",
#         'collaborators': [
#             {
#                 'name': 'Whoever',
#                 'md5': 'thisisafakemd5'
#             }
#         ]
#     }
# 
    return jsonify(**data)


@translator_api_blueprint.route("/apps/bundles/<language>/<target>/updateMessage", methods=["GET", "PUT", "POST"])
@requires_golab_api_login
@cross_origin()
@api
def bundle_update(language, target):
    app_url = request.values.get('app_url')
    try:
        request_data = request.get_json(force=True, silent=True) or {}
    except ValueError:
        request_data = {}
    key = request_data.get("key")
    value = request_data.get("value")

    if key is None or value is None:
        return jsonify(**{"result": "error"})

    user = current_golab_user()
    translation_url, original_messages, metadata = extract_local_translations_url(app_url, force_local_cache = True)
    translated_messages = { key : value }

    add_full_translation_to_app(user, app_url, translation_url, metadata, language, target, translated_messages, original_messages, from_developer = False)
    from appcomposer.translator.tasks import task_synchronize_single_app
    task_synchronize_single_app.delay("update", app_url)

    return jsonify(**{"result": "success"})

@translator_api_blueprint.route('/apps')
@public
@cross_origin()
@api
def api_app():
    app_url = request.args.get('app_url')
    app_thumb = None
    app_link = None
    name = None
    desc = None

    for repo_app in db.session.query(RepositoryApp).filter_by(url = app_url).all():
        if repo_app.name is not None:
            name = repo_app.name
        if repo_app.app_thumb is not None:
            app_thumb = repo_app.app_thumb
        if repo_app.description is not None:
            desc = repo_app.description
        if repo_app.app_link is not None:
            app_link = repo_app.app_link

    translation_url, original_messages, metadata = extract_local_translations_url(app_url, force_local_cache = True)
    translations, generic_dependencies = retrieve_translations_stats(translation_url, original_messages)
    register_app_url(app_url, translation_url, metadata)

    app_data = {
        'url' : app_url,
        'app_thumb': app_thumb,
        'app_link' : app_link,
        'name' : name,
        'desc' : desc,
        'translations' : translations,
        'generic_dependencies': generic_dependencies,
    }
    return jsonify(**app_data)

@translator_api_blueprint.route('/apps/bundles/<language>/<target>')
@requires_golab_api_login
@cross_origin()
@api
def api_translate(language, target):
    app_url = request.args.get('app_url')

    errors = []
    if not app_url:
        errors.append("'app_url' argument missing")
    if not language:
        errors.append("'lang' argument missing")
    if not target:
        errors.append("'target' argument missing")
    if errors:
        return '; '.join(errors), 400

    translation_url, original_messages, metadata = extract_local_translations_url(app_url)
    translation = {}

    stored_translations, from_developer, automatic = retrieve_stored(translation_url, language, target)
    suggestions = retrieve_suggestions(original_messages, language, target, stored_translations)
    for key, original_message_pack in original_messages.iteritems():
        # We still store the message itself (useful for other things, such as storing and maintaining it
        # in MongoDB contacted by Shindig). However, we do not display these messages to the final user
        if not original_message_pack['same_tool']:
            continue

        value = original_message_pack['text']
        stored = stored_translations.get(key, {})
        current_suggestions = list(suggestions.get(key, []))
        current_target = stored.get('value')

        if from_developer:
            can_edit = not stored.get('from_developer', True)
        else:
            can_edit = True

        if value:
            translation[key] = {
                'source' : value,
                'target' : current_target,
                'from_default' : stored.get('from_default', False),
                'suggestions' : current_suggestions,
                'can_edit' : can_edit,
                'format': original_message_pack.get('format', 'plain'),
            }

    app_thumb = None
    name = None
    for repo_app in db.session.query(RepositoryApp).filter_by(url = app_url).all():
        if repo_app.name is not None:
            name = repo_app.name
        if repo_app.app_thumb is not None:
            app_thumb = repo_app.app_thumb
        if name and app_thumb:
            break

    update_user_status(language, target, app_url, current_golab_user())
    users_status = get_user_status(language, target, app_url, current_golab_user())

    response = {
        'url' : app_url,
        'app_thumb' : app_thumb,
        'name' : name,
        'translation' : translation,
        'modificationDate': users_status['modificationDate'],
        'modificationDateByOther': users_status['modificationDateByOther'],
        'automatic': automatic and not from_developer,
        'preview': automatic,
    }

    if False:
        response = json.dumps(response, indent = 4)
        return "<html><body>%s</body></html>" % response
    return jsonify(**response)


