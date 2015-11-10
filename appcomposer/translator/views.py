"""
New translator
"""

import os
import time
import json
import zipfile
import hashlib
import StringIO
import datetime
import traceback
from functools import wraps

from collections import OrderedDict

from sqlalchemy import distinct, func
from sqlalchemy.orm import joinedload_all

from flask import Blueprint, make_response, render_template, request, flash, redirect, url_for, jsonify, Response, send_file
from flask.ext.wtf import Form
from flask.ext.wtf.file import FileField
from flask.ext.admin.form import Select2Field
from flask.ext.cors import cross_origin
from wtforms.fields.html5 import URLField
from wtforms.validators import url, required

from appcomposer.db import db
from appcomposer.application import app
from appcomposer.models import TranslatedApp, TranslationUrl, TranslationBundle, RepositoryApp, GoLabOAuthUser, ActiveTranslationMessage, TranslationMessageHistory
from appcomposer.login import requires_golab_login, current_golab_user
from appcomposer.translator.mongodb_pusher import retrieve_mongodb_contents
from appcomposer.translator.exc import TranslatorError
from appcomposer.translator.languages import obtain_groups, obtain_languages
from appcomposer.translator.utils import extract_local_translations_url, extract_messages_from_translation
from appcomposer.translator.ops import add_full_translation_to_app, retrieve_stored, retrieve_suggestions, retrieve_translations_stats, register_app_url, get_latest_synchronizations, update_user_status, get_user_status
from appcomposer.translator.utils import bundle_to_xml, bundle_to_jquery_i18n, bundle_to_json, bundle_to_graasp_json, bundle_to_properties, url_to_filename, messages_to_xml, NO_CATEGORY, NO_TOOL

import flask.ext.cors.core as cors_core
cors_core.debugLog = lambda *args, **kwargs : None

translator_blueprint = Blueprint('translator', __name__, static_folder = '../../translator3/dist/', static_url_path = '/web')

#
# Use @public to mark that a method is intentionally public
# 
def public(func): return func

def api(func):
    """If a method is annotated with api, we will check regular errors and wrap them to a JSON document"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TranslatorError as e:
            if e.code == 500:
                app.logger.error("Error processing request: %s" % e, exc_info = True)
                print("Error processing request: %s" % e)
            traceback.print_exc()
            return make_response(json.dumps({ 'result' : 'error', 'message' : e.args[0] }), e.code)
        except Exception as e:
            app.logger.error("Unknown error processing request: %s" % e, exc_info = True)
            print("Unknown error processing request: %s" % e)
            traceback.print_exc()
            return make_response(json.dumps({ 'result' : 'error', 'message' : e.args[0] }), 500)
    return wrapper

@translator_blueprint.route('/')
@requires_golab_login
def translator_index():
    return redirect(url_for('.static', filename='index.html'))


@translator_blueprint.route("/api/user/authenticate")
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

@translator_blueprint.route("/api/user/default_language")
@public
@cross_origin()
@api
def guess_default_language():
    return jsonify(language = _guess_default_language())

@translator_blueprint.route('/select')
@public
def select_translations():
    app_url = request.args.get('app_url')
    language = request.args.get('lang')
    target = request.args.get('target')

    if app_url and language and target:
        return redirect(url_for('.api_translate', app_url = app_url, lang = language, target = target))

    targets = obtain_groups()
    languages = list(obtain_languages().iteritems())
    languages.sort(lambda x1, x2 : cmp(x1[1], x2[1]))
    return render_template("translator/select_translations.html", targets = targets, languages = languages)

@translator_blueprint.route('/api/apps/repository')
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
            translated_languages = json.loads(repo_app.translation_percent) or {}
        except ValueError:
            translated_languages = {}

        languages = {}
        for translated_lang, progress in translated_languages.iteritems():
            translated_lang_simplified = translated_lang.split('_')[0]
            translated_lang_country = '_'.join(translated_lang.split('_')[:2])
            languages[translated_lang_simplified] = {
                'original' : translated_lang_country in original_languages,
                'progress' : progress
            }

        # TODO: add Graasp and so on, plus use the retrieval method (e.g., labs/retrieve.json vs. apps/retrieve.json) to know whether it's one thing or the other
        if repo_app.repository == 'golabz' and (repo_app.app_link.startswith('http://www.golabz.eu/app/') or repo_app.app_link.startswith('http://www.golabz.eu/apps/') or repo_app.app_link.startswith('http://www.golabz.eu/content/')):
            where = applications
        elif repo_app.repository == 'golabz' and (repo_app.app_link.startswith('http://www.golabz.eu/lab/') or repo_app.app_link.startswith('http://www.golabz.eu/labs/')):
            where = laboratories
        else:
            where = others

        where.append({
            'original_languages' : original_languages,
            'original_languages_simplified' : original_languages_simplified,
            'translated_languages' : translated_languages,
            'languages' : languages,
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



@translator_blueprint.route('/api/info/languages')
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

@translator_blueprint.route('/api/info/groups')
@public
@cross_origin()
@api
def api_groups():
    return jsonify(**obtain_groups())

@translator_blueprint.route("/api/apps/bundles/<language>/<target>/checkModifications", methods=["GET"])
@requires_golab_login
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


@translator_blueprint.route("/api/apps/bundles/<language>/<target>/updateMessage", methods=["GET", "PUT", "POST"])
@requires_golab_login
@cross_origin()
@api
def bundle_update(language, target):
    app_url = request.values.get('app_url')
    key = request.values.get("key")
    value = request.values.get("value")

    if key is None or value is None:
        return jsonify(**{"result": "error"})

    user = current_golab_user()
    translation_url, original_messages, metadata = extract_local_translations_url(app_url, force_local_cache = True)
    translated_messages = { key : value }

    add_full_translation_to_app(user, app_url, translation_url, metadata, language, target, translated_messages, original_messages, from_developer = False)
    from appcomposer.translator.tasks import synchronize_apps_cache_wrapper
    synchronize_apps_cache_wrapper.delay("update", app_url)


    return jsonify(**{"result": "success"})

@translator_blueprint.route('/api/apps')
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
    translations = retrieve_translations_stats(translation_url, original_messages)
    register_app_url(app_url, translation_url, metadata)

    app_data = {
        'url' : app_url,
        'app_thumb': app_thumb,
        'app_link' : app_link,
        'name' : name,
        'desc' : desc,
        'translations' : translations,
    }
    return jsonify(**app_data)

@translator_blueprint.route('/api/apps/bundles/<language>/<target>')
@requires_golab_login
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

        translation[key] = {
            'source' : value,
            'target' : current_target,
            'from_default' : stored.get('from_default', False),
            'suggestions' : current_suggestions,
            'can_edit' : can_edit
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

@translator_blueprint.route('/lib.js')
@public
@cross_origin()
def widget_js():
    # You can play with this app by running $("body").append("<script src='http://localhost:5000/translator/lib.js'></script>");
    # In the console of the golabz app
    try:
        repo_app = db.session.query(RepositoryApp).filter_by(app_link = request.referrer).first()
        if repo_app is None:
            resp = make_response("// Repository application not found")
            resp.content_type = 'application/javascript'
            return resp
        if not repo_app.translatable:
            resp = make_response("// Repository application found; not translatable")
            resp.content_type = 'application/javascript'
            return resp

        translations = (repo_app.original_translations or '').split(',')
        translations = [ t.split('_')[0] for t in translations ]
        # By default, translatable apps are in English
        if 'en' not in translations:
            translations.insert(0, 'en')
        try:
            translation_percent = json.loads(repo_app.translation_percent or '{}')
        except ValueError:
            translation_percent = {}
        for language, percent in translation_percent.iteritems():
            if percent >= 0.5:
                lang_code = language.split("_")[0]
                if lang_code not in translations:
                    translations.append(lang_code)
        
        human_translations = []
        for lang_code in translations:
            if lang_code in LANGUAGES:
                human_translations.append(LANGUAGES[lang_code])
            elif u'%s_ALL' % lang_code in LANGUAGES:
                human_translations.append(LANGUAGES[u'%s_ALL' % lang_code])
            else:
                human_translations.append(lang_code)

        html_url = url_for('.static', filename="index.html", _external = True)
        link = '%s#/app/%s' % (html_url, repo_app.url)
        str_translations = u', '.join(human_translations)

        if str_translations and link:
            resp = make_response(render_template("translator/lib.js", translations = str_translations, link = link))
        else:
            resp = make_response("// App found and transtable, but no translation found")
        resp.content_type = 'application/javascript'
        return resp
    except Exception as e:
        traceback.print_exc()
        resp = make_response("""// Error: %s """ % repr(e))
        resp.content_type = 'application/javascript'
        return resp

        

TARGET_CHOICES = []
TARGETS = obtain_groups()
for target_code in sorted(TARGETS):
    TARGET_CHOICES.append((target_code, TARGETS[target_code]))

LANGUAGE_CHOICES = []
LANGUAGES = obtain_languages()
for lang_code in sorted(LANGUAGES):
    LANGUAGE_CHOICES.append((lang_code, LANGUAGES[lang_code]))

class UploadForm(Form):
    url = URLField(u"App URL", validators=[url(), required()])
    language = Select2Field(u"Language", choices = LANGUAGE_CHOICES, validators = [ required() ])
    target = Select2Field(u"Target age", choices = TARGET_CHOICES, validators = [ required() ], default = "ALL")
    opensocial_xml = FileField(u'OpenSocial XML file', validators = [required()])

def _guess_default_language():
    best_match = request.accept_languages.best_match([ lang_code.split('_')[0] for lang_code in LANGUAGES ])
    default_language = None
    if best_match is not None:
        if best_match in LANGUAGES:
            default_language = best_match
        else:
            lang_codes = [ lang_code for lang_code in LANGUAGES if lang_code.startswith('%s_' % best_match) ]
            if lang_codes:
                default_language = lang_codes[0]
    return default_language

@translator_blueprint.route('/dev/upload/', methods = ('GET', 'POST'))
@requires_golab_login
def translation_upload():
    default_language = _guess_default_language()
    if default_language:
        form = UploadForm(language = default_language)
    else:
        form = UploadForm()

    if form.validate_on_submit():
        errors = False
        app_url = form.url.data

        try:
            translation_url, original_messages, metadata = extract_local_translations_url(app_url)
        except Exception as e:
            traceback.print_exc()
            form.url.errors = [unicode(e)]
            errors = True

        xml_contents = form.opensocial_xml.data.read()
        if isinstance(xml_contents, str):
            xml_contents = unicode(xml_contents, 'utf8')
        try:
            translated_messages, metadata = extract_messages_from_translation(translation_url, xml_contents)
        except Exception as e:
            traceback.print_exc()
            form.opensocial_xml.errors = [unicode(e)]
            errors = True
        
        if not errors:
            language = form.language.data
            target = form.target.data
            add_full_translation_to_app(current_golab_user(), app_url, translation_url, metadata, language, target, translated_messages, original_messages, from_developer = False)
            from appcomposer.translator.tasks import synchronize_apps_cache_wrapper
            synchronize_apps_cache_wrapper.delay("upload")
            flash("Contents successfully added")

    return render_template('translator/translations_upload.html', form=form)

@translator_blueprint.route('/dev/')
@public
def translations():
    return render_template("translator/translations.html")

@translator_blueprint.route('/dev/users')
@requires_golab_login
def translation_users():
    users = db.session.query(GoLabOAuthUser.display_name, GoLabOAuthUser.email).all()
    users_by_gravatar = OrderedDict()

    for display_name, email in users:
        gravatar_url = 'http://gravatar.com/avatar/%s?s=40&d=identicon' % hashlib.md5(email).hexdigest()
        users_by_gravatar[gravatar_url] = display_name.strip().replace('.', ' ').title().split(' ')[0]

    return render_template('translator/users.html', users_by_gravatar = users_by_gravatar)

@translator_blueprint.route('/dev/sync/', methods = ['GET', 'POST'])
@requires_golab_login
def sync_translations():
    since_id = request.args.get('since')
    if since_id:
        try:
            since_id = int(since_id)
        except ValueError:
            since_id = None
    
    latest_synchronizations = get_latest_synchronizations()
    finished = False
    for latest_synchronization in latest_synchronizations:
        if latest_synchronization['id'] > since_id and latest_synchronization['end'] is not None:
            finished = True
            break

    if latest_synchronizations:
        latest_id = latest_synchronizations[-1]['id']
    else:
        latest_id = 0

    if request.method == 'POST':
        from appcomposer.translator.tasks import synchronize_apps_no_cache_wrapper
        synchronize_apps_no_cache_wrapper.delay("manual sync request")
        submitted = True
        return redirect(url_for('.sync_translations', since = latest_id))
    else:
        submitted = False
    return render_template("translator/sync.html", latest_synchronizations = latest_synchronizations, since_id = since_id, submitted = submitted, current_datetime = datetime.datetime.utcnow(), finished = finished)


@translator_blueprint.route('/dev/sync/debug/')
def sync_debug():
    # Just in case the debug value changes during the load of modules
    if not app.config['DEBUG']:
        return "Not in debug mode!"

    now = datetime.datetime.utcnow()
    t0 = time.time()
    from appcomposer.translator.translation_listing import synchronize_apps_no_cache
    synchronize_apps_no_cache("sync debug")
    tf = time.time()
    return "<html><body>synchronization process finished (%.2f seconds): %s </body></html>" % (tf - t0, now)

@translator_blueprint.route('/dev/urls/')
@public
def translations_urls():
    urls = {}
    for db_url in db.session.query(TranslationUrl).options(joinedload_all('bundles')):
        urls[db_url.url] = []
        for bundle in db_url.bundles:
            urls[db_url.url].append({
                'from_developer' : bundle.from_developer,
                'target' : bundle.target,
                'lang' : bundle.language,
            })
    return render_template("translator/translations_urls.html", urls = urls)

def _sort_dicts_by_datetime(dictionary):
    all_values = [ (key, value) for key, value in dictionary.iteritems() ]
    all_values.sort(lambda (k1, v1), (k2, v2) : cmp(v1.get('last_change'), v2.get('last_change')), reverse = True)
    new_dict = OrderedDict()
    for key, value in all_values:
        new_dict[key] = value
    return new_dict

def _dict2sorted_list(dictionary, key_name = 'id'):
    all_values = [ (key, value) for key, value in dictionary.iteritems() ]
    all_values.sort(lambda (k1, v1), (k2, v2) : cmp(v1.get('last_change'), v2.get('last_change')), reverse = True)
    sorted_list = []
    for key, value in all_values:
        value[key_name] = key
        sorted_list.append(value)
    return sorted_list

SITE_ROOT = '.'

@translator_blueprint.route('/dev/apps/')
@public
def translations_apps():
    # Takes 1ms to load these two files. And putting it here is better for being able to change the code dynamically
    apps_angular_code = open(os.path.join(SITE_ROOT, "appcomposer/templates/translator/apps_angular_js.js")).read()
    apps_angular_html = open(os.path.join(SITE_ROOT, "appcomposer/templates/translator/apps_angular_html.html")).read()

    return render_template("translator/translations_apps2.html", angular_js = apps_angular_code, angular_html = apps_angular_html, NAMES = NAMES)

@translator_blueprint.route('/dev/apps/<path:app_url>')
@public
def translations_apps_filtered(app_url):
    app = db.session.query(TranslatedApp).filter_by(url = app_url).first()
    if app is None:
        return render_template("translator/error.html", message = "App does not exist"), 404

    # Takes 1ms to load these two files. And putting it here is better for being able to change the code dynamically
    apps_angular_code = open(os.path.join(SITE_ROOT, "appcomposer/templates/translator/apps_angular_js.js")).read()
    apps_angular_html = open(os.path.join(SITE_ROOT, "appcomposer/templates/translator/apps_angular_html.html")).read()

    return render_template("translator/translations_apps2.html", angular_js = apps_angular_code, angular_html = apps_angular_html, NAMES = NAMES, app_url = app_url)

@translator_blueprint.route('/dev/apps/failing/')
@public
def apps_failing():
    failing_apps = db.session.query(RepositoryApp).filter_by(failing = True).all()
    return render_template("translator/failing_apps.html", failing_apps = failing_apps)

@translator_blueprint.route('/dev/apps/apps.json')
@public
def translations_apps_json():
    requested_app_url = request.args.get('app_url', None)
    global_max_date = db.session.query(func.max(ActiveTranslationMessage.datetime)).first()
    if global_max_date:
        global_max_date = global_max_date[0]
        if request.if_modified_since == global_max_date:
            return Response(status=304)
    

    golab_apps = {}
    other_apps = {}
    golab_app_by_url = {}
    for app in db.session.query(RepositoryApp).all():
        golab_app_by_url[app.url] = {
                'app_thumb' : app.app_thumb,
                'url' : app.url,
                'app_link' : app.app_link,
                'name' : app.name,
            }

    categories_per_bundle_id = {
        # bundle_id : set(category1, category2)
    }
    for category, bundle_id in db.session.query(distinct(ActiveTranslationMessage.category), ActiveTranslationMessage.bundle_id).group_by(ActiveTranslationMessage.category, ActiveTranslationMessage.bundle_id).all():
        if bundle_id not in categories_per_bundle_id:
            categories_per_bundle_id[bundle_id] = set()
        if category is None:
            category = NO_CATEGORY
        categories_per_bundle_id[bundle_id].add(category)

    tools_per_bundle_id = {
        # bundle_id : set(tool1, tool2)
    }
    for tool_id, bundle_id in db.session.query(distinct(ActiveTranslationMessage.tool_id), ActiveTranslationMessage.bundle_id).group_by(ActiveTranslationMessage.tool_id, ActiveTranslationMessage.bundle_id).all():
        if bundle_id not in tools_per_bundle_id:
            tools_per_bundle_id[bundle_id] = set()
        if tool_id is None:
            tool_id = NO_TOOL
        tools_per_bundle_id[bundle_id].add(tool_id)

    max_date_per_translation_url_id = {}
    for max_date, translation_url_id in (db.session.query(func.max(ActiveTranslationMessage.datetime), TranslationBundle.translation_url_id)
                                            .filter(
                                                ActiveTranslationMessage.bundle_id == TranslationBundle.id, 
                                                ActiveTranslationMessage.history_id == TranslationMessageHistory.id)
                                            .group_by(TranslationBundle.translation_url_id).all()):
        max_date_per_translation_url_id[translation_url_id] = max_date

    for app in db.session.query(TranslatedApp).options(joinedload_all('translation_url.bundles')):
        if requested_app_url is not None and requested_app_url != app.url:
            continue

        if app.url in golab_app_by_url:
            current_apps = golab_apps
        else:
            current_apps = other_apps
        current_apps[app.url] = {
            'categories' : set(),
            'tools' : set(),
            'translations' : [],
        }
        if app.translation_url is not None:
            current_apps[app.url]['last_change'] = max_date_per_translation_url_id.get(app.translation_url_id, None)
            for bundle in app.translation_url.bundles:
                current_apps[app.url]['translations'].append({
                    'from_developer' : bundle.from_developer,
                    'target' : bundle.target,
                    'lang' : bundle.language,
                })
                
                for category in categories_per_bundle_id.get(bundle.id, []):
                    current_apps[app.url]['categories'].add(category)

                for tool_id in tools_per_bundle_id.get(bundle.id, []):
                    current_apps[app.url]['tools'].add(tool_id)

        current_apps[app.url]['categories'] = sorted(list(current_apps[app.url]['categories']))
        if len(current_apps[app.url]['categories']) == 1 and current_apps[app.url]['categories'][0] is NO_CATEGORY:
            current_apps[app.url]['categories'] = []

        current_apps[app.url]['categories'] = [ { 'name' : cat } for cat in current_apps[app.url]['categories'] ]

        current_apps[app.url]['tools'] = sorted(list(current_apps[app.url]['tools']))
        if len(current_apps[app.url]['tools']) == 1 and current_apps[app.url]['tools'][0] is NO_TOOL:
            current_apps[app.url]['tools'] = []

        current_apps[app.url]['tools'] = [ { 'name' : tool_id } for tool_id in current_apps[app.url]['tools'] ]


    golab_apps = _dict2sorted_list(golab_apps, key_name = 'app_url')
    other_apps = _dict2sorted_list(other_apps, key_name = 'app_url')
    for app in golab_apps:
        app['app_url_hash'] = hash(app['app_url'])
        app_data = golab_app_by_url[app['app_url']]
        app['app_thumb'] = app_data['app_thumb']
        app['app_link'] = app_data['app_link']
        app['app_name'] = app_data['name']
        app['last_change'] = app['last_change'].strftime('%Y-%m-%d %H:%M:%SZ')

    for app in other_apps:
        app['app_url_hash'] = hash(app['app_url'])
        app['last_change'] = app['last_change'].strftime('%Y-%m-%d %H:%M:%SZ')

    response = {
        'apps' : [],
    }
    if golab_apps:
        response['apps'].append({
                'appset_id' : 'golab_apps',
                'name' : 'Go-Lab repository applications',
                'apps' : golab_apps,
            })
    if other_apps:
        response['apps'].append({
                'appset_id' : 'other_apps',
                'name' : 'Other applications',
                'apps' : other_apps,
            })

    response = Response(json.dumps(response, indent = 0), content_type = 'application/json')
    response.last_modified = global_max_date
    response.headers['Cache-Control'] = 'must-revalidate'
    return response

FORMAT_OPENSOCIAL = 'opensocial'
FORMAT_JQUERY_I18N = 'jquery_i18n'
FORMAT_JSON = 'json'
FORMAT_PROPERTIES = 'properties'
FORMAT_GRAASP_JSON = 'graasp_json'

SERIALIZERS = {
    FORMAT_OPENSOCIAL : bundle_to_xml,
    FORMAT_JQUERY_I18N : bundle_to_jquery_i18n,
    FORMAT_PROPERTIES : bundle_to_properties,
    FORMAT_JSON : bundle_to_json,
    FORMAT_GRAASP_JSON: bundle_to_graasp_json,
}

MIMETYPES = {
    FORMAT_OPENSOCIAL : 'application/xml',
    FORMAT_JQUERY_I18N : 'application/json',
    FORMAT_JSON : 'application/json',
    FORMAT_PROPERTIES : 'text/plain; charset=utf-8',
    FORMAT_GRAASP_JSON: 'application/json',
}

EXTENSIONS = {
    FORMAT_OPENSOCIAL : 'xml',
    FORMAT_JQUERY_I18N : 'json',
    FORMAT_JSON : 'json',
    FORMAT_PROPERTIES : 'properties',
    FORMAT_GRAASP_JSON: 'json',
}

NAMES = OrderedDict()
NAMES[FORMAT_OPENSOCIAL] = "OpenSocial"
NAMES[FORMAT_PROPERTIES] = "Properties file"
NAMES[FORMAT_JSON] = "JSON"
NAMES[FORMAT_JQUERY_I18N] = "jQuery i18n plug-in"
NAMES[FORMAT_GRAASP_JSON] = "Graasp JSON"


# 
# Old openSocial links (not indexed anymore)
# 

@translator_blueprint.route('/dev/apps/<lang>/<target>/<path:app_url>')
@public
def translations_app_xml(lang, target, app_url):
    return _translate_app(lang, target, app_url, output_format = FORMAT_OPENSOCIAL)

@translator_blueprint.route('/dev/apps/all.zip')
@public
def translations_app_all_zip():
    return _translate_app_all_zip(output_format = FORMAT_OPENSOCIAL)

@translator_blueprint.route('/dev/apps/all/<path:app_url>')
@public
def translations_app_url_zip(app_url):
    return _translations_app_url_zip(app_url, output_format = FORMAT_OPENSOCIAL)

@translator_blueprint.route('/dev/urls/<lang>/<target>/<path:url>')
@public
def translations_url_xml(lang, target, url):
    return _translate_url(lang, target, url, output_format = FORMAT_OPENSOCIAL)

# 
# Generic links
# 

@translator_blueprint.route('/dev/apps/<format_key>/<lang>/<target>/<path:app_url>')
@public
def translations_app_format(format_key, lang, target, app_url):
    if format_key not in NAMES:
        return "Invalid format", 404
    return _translate_app(lang, target, app_url, output_format = format_key)

@translator_blueprint.route('/dev/apps/<format_key>/all.zip')
@public
def translations_app_all_format_zip(format_key):
    if format_key not in NAMES:
        return "Invalid format", 404
    return _translate_app_all_zip(output_format = format_key)

@translator_blueprint.route('/dev/apps/<format_key>/<path:app_url>')
@public
def translations_app_url_format_zip(format_key, app_url):
    if format_key not in NAMES:
        return "Invalid format", 404
    return _translations_app_url_zip(app_url, output_format = format_key)

@translator_blueprint.route('/dev/urls/<format_key>/<lang>/<target>/<path:url>')
@public
def translations_url_format(format_key, lang, target, url):
    if format_key not in NAMES:
        return "Invalid format", 404
    return _translate_url(lang, target, url, output_format = format_key)

# 
# Real implementations (format agnostic)
# 

def _translate_app(lang, target, app_url, output_format):
    translation_app = db.session.query(TranslatedApp).filter_by(url = app_url).first()
    if translation_app is None:
        return "Translation App not found in the database", 404

    return _translate_url(lang, target, translation_app.translation_url.url, output_format = output_format)

def _translate_app_all_zip(output_format):
    serializer = SERIALIZERS[output_format]
    extension = EXTENSIONS[output_format]

    translated_apps = db.session.query(TranslatedApp).filter_by().all()
    sio = StringIO.StringIO()
    zf = zipfile.ZipFile(sio, 'w')

    for translated_app in translated_apps:
        translated_app_filename = url_to_filename(translated_app.url)
        if translated_app.translation_url:
            for bundle in translated_app.translation_url.bundles:
                xml_contents = serializer(bundle)
                zf.writestr('%s_%s.%s' % (os.path.join(translated_app_filename, bundle.language), bundle.target, extension), xml_contents)
    zf.close()

    resp = make_response(sio.getvalue())
    resp.content_type = 'application/zip'
    return resp

def _translations_app_url_zip(app_url, output_format):
    serializer = SERIALIZERS[output_format]
    extension = EXTENSIONS[output_format]

    translated_app = db.session.query(TranslatedApp).filter_by(url = app_url).first()
    if translated_app is None:
        return "Translation App not found in the database", 404
   
    category = request.args.get('category', None)
    tool_id = request.args.get('tool_id', None)
    sio = StringIO.StringIO()
    zf = zipfile.ZipFile(sio, 'w')
    translated_app_filename = url_to_filename(translated_app.url)
    if translated_app.translation_url:
        for bundle in translated_app.translation_url.bundles:
            xml_contents = serializer(bundle, category, tool_id)
            zf.writestr('%s_%s.%s' % (bundle.language, bundle.target, extension), xml_contents)
    zf.close()

    resp = make_response(sio.getvalue())
    resp.content_type = 'application/zip'
    resp.headers['Content-Disposition'] = 'attachment;filename=%s.zip' % translated_app_filename
    return resp

def _translate_url(lang, target, url, output_format):
    
    translation_url = db.session.query(TranslationUrl).filter_by(url = url).first()
    if translation_url is None:
        return "Translation URL not found in the database", 404

    bundle = db.session.query(TranslationBundle).filter_by(translation_url = translation_url, language = lang, target = target).first()
    if bundle is None:
        return "Translation URL found, but no translation for that language or target"

    category = request.args.get('category', None)
    tool_id = request.args.get('tool_id', None)
    messages_xml = SERIALIZERS[output_format](bundle, category, tool_id)
    resp = make_response(messages_xml)
    resp.content_type = MIMETYPES[output_format]
    return resp

@translator_blueprint.route('/dev/mongodb/')
@public
def translations_mongodb():
    collections = {}
    contents = retrieve_mongodb_contents()
    for collection, collection_contents in contents.iteritems():
        collections[collection] = json.dumps(collection_contents, indent = 4)
    return render_template("translator/mongodb.html", collections = collections)

@translator_blueprint.route('/dev/mongodb/apps/')
@public
def translations_mongodb_apps():
    apps = {}
    collections = retrieve_mongodb_contents()
    for app in collections['bundles']:
        url = app['spec']
        bundle = app['bundle']
        lang, target = bundle.rsplit('_', 1)
        if url not in apps:
            apps[url] = []

        apps[url].append({
            'target' : target,
            'lang' : lang
        })

    return render_template("translator/mongodb_listing.html", apps = apps, title = "Apps", xml_method = '.translations_mongodb_apps_xml')

@translator_blueprint.route('/dev/mongodb/urls/')
@public
def translations_mongodb_urls():
    apps = {}
    collections = retrieve_mongodb_contents()
    for app in collections['translation_urls']:
        url = app['url']
        bundle = app['bundle']
        lang, target = bundle.rsplit('_', 1)
        if url not in apps:
            apps[url] = []

        apps[url].append({
            'target' : target,
            'lang' : lang
        })

    return render_template("translator/mongodb_listing.html", apps = apps, title = "URLs", xml_method = '.translations_mongodb_urls_xml')

@translator_blueprint.route('/dev/mongodb/apps/<lang>/<target>/<path:url>')
@public
def translations_mongodb_apps_xml(lang, target, url):
    apps = {}
    collections = retrieve_mongodb_contents()
    for app in collections['bundles']:
        cur_url = app['spec']
        cur_bundle = app['bundle']
        cur_lang, cur_target = cur_bundle.rsplit('_', 1)
        if cur_url == url and cur_lang == lang and cur_target == target:
            resp = make_response(messages_to_xml(json.loads(app['data'])))
            resp.content_type = 'application/xml'
            return resp

    return "Not found", 404

@translator_blueprint.route('/dev/mongodb/urls/<lang>/<target>/<path:url>')
@public
def translations_mongodb_urls_xml(lang, target, url):
    apps = {}
    collections = retrieve_mongodb_contents()
    for app in collections['translation_urls']:
        cur_url = app['url']
        cur_bundle = app['bundle']
        cur_lang, cur_target = cur_bundle.rsplit('_', 1)
        if cur_url == url and cur_lang == lang and cur_target == target:
            resp = make_response(messages_to_xml(json.loads(app['data'])))
            resp.content_type = 'application/xml'
            return resp

    return "Not found", 404

