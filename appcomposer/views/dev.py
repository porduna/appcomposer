import os
import time
import json
import zipfile
import StringIO
import datetime
import traceback
import requests

from collections import OrderedDict, defaultdict

from sqlalchemy import distinct, func, or_, not_
from sqlalchemy.orm import joinedload

from flask import Blueprint, make_response, render_template, request, flash, redirect, url_for, jsonify, Response, current_app
from flask_wtf import Form
from flask_wtf.file import FileField
from flask_admin.form import Select2Field
from flask_cors import cross_origin
from wtforms.fields.html5 import URLField
from wtforms.validators import url, required

from appcomposer.db import db
from appcomposer.models import TranslatedApp, TranslationUrl, TranslationBundle, RepositoryApp, ActiveTranslationMessage, TranslationMessageHistory
from appcomposer.login import requires_golab_login, current_golab_user
from appcomposer.translator.mongodb_pusher import retrieve_mongodb_contents, retrieve_mongodb_apps, retrieve_mongodb_urls, retrieve_mongodb_app, retrieve_mongodb_translation_url
from appcomposer.languages import obtain_groups, obtain_languages
from appcomposer.translator.extractors import extract_local_translations_url, extract_messages_from_translation
from appcomposer.translator.ops import add_full_translation_to_app, get_latest_synchronizations
from appcomposer.translator.utils import bundle_to_xml, bundle_to_jquery_i18n, bundle_to_json, bundle_to_graasp_json, bundle_to_properties, url_to_filename, messages_to_xml, NO_CATEGORY, NO_TOOL
from appcomposer.translator.suggestions import translate_texts

from appcomposer.utils import public
from appcomposer.languages import LANGUAGES_PER_NAME, LANGUAGE_NAMES_PER_CODE, WRONG_LANGUAGES_PER_CORRECT_NAME, WRONG_LANGUAGES, LANGUAGE_THRESHOLD, sort_languages, guess_default_language

import flask_cors.core as cors_core
cors_core.debugLog = lambda *args, **kwargs : None


translator_dev_blueprint = Blueprint('translator_dev', __name__, static_folder = '../../translator3/dist/', static_url_path = '/web')

@translator_dev_blueprint.route('/supported_languages.json')
@public
@cross_origin()
def supported_languages():
    languages = sorted([ (name, code) for name, code in LANGUAGES_PER_NAME.items() if not '_' in code ], lambda (name1, code1), (name2, code2) : cmp(name1, name2))
    visible_languages = [ key.split('_')[0] for key in obtain_languages().keys() ]
    return jsonify(languages=languages, golab_languages=visible_languages, mappings=WRONG_LANGUAGES_PER_CORRECT_NAME)

@translator_dev_blueprint.route('/supported_languages.html')
@public
@cross_origin()
def supported_languages_human():
    languages = sorted([ (name, code) for name, code in LANGUAGES_PER_NAME.items() if not '_' in code ], lambda (name1, code1), (name2, code2) : cmp(name1, name2))
    visible_languages = [ key.split('_')[0] for key in obtain_languages().keys() ]
    return render_template("translator/supported_languages.html", languages=languages, wrong=WRONG_LANGUAGES_PER_CORRECT_NAME, visible_languages=visible_languages)

# @translator_dev_blueprint.route('/languages/apps.json')
# @public
# def languages_apps():
#     from appcomposer.translator.tasks import GOLAB_REPO
#     apps = db.session.query(RepositoryApp).filter_by(repository=GOLAB_REPO).filter(not_(RepositoryApp.external_id.like('%-%'))).all()
#     by_repo = {
#         # id: [lang1, lang2...]
#     }
#     for app in apps:
#         app_languages = []
#         for lang in app.languages:
#             app_languages.append(lang.language.language.split('_')[0])
#         by_repo[app.external_id] = app_languages
#     return jsonify(by_repo)
# 
# @translator_dev_blueprint.route('/languages/labs.json')
# @public
# def languages_labs():
#     from appcomposer.translator.tasks import GOLAB_REPO
#     labs = db.session.query(RepositoryApp).filter_by(repository=GOLAB_REPO).filter(RepositoryApp.external_id.like('%-%')).all()
#     by_repo = {
#         # id: [lang1, lang2...]
#     }
#     for lab in labs:
#         external_id = lab.external_id.split('-')[0]
#         lab_languages = set(by_repo.get(external_id, []))
#         for lang in lab.languages:
#             lab_languages.add(lang.language.language.split('_')[0])
#         by_repo[external_id] = list(lab_languages)
#     return jsonify(by_repo)

@translator_dev_blueprint.route('/languages.json')
@public
def languages_labs():
    from appcomposer.translator.tasks import GOLAB_REPO
    labs = db.session.query(RepositoryApp).filter_by(repository=GOLAB_REPO).all()
    by_repo = {
        # id: [lang1, lang2...]
    }
    default_level = 0.7
    provided_level = request.args.get('level')

    level = default_level
    if provided_level:
        try:
            level = float(provided_level)
        except:
            pass

    for lab in labs:
        external_id = lab.external_id.split('-')[0]
        lab_languages = set(by_repo.get(external_id, []))
        for lang, level in json.loads(lab.translation_percent or '{}').items():
            if level > 0.7:
                lab_languages.add(lang.split('_')[0])
        by_repo[external_id] = list(lab_languages)

    for lang_pack in by_repo.values():
        if len(lang_pack) == 0:
            lang_pack.append('en')

    return jsonify(by_repo)

@translator_dev_blueprint.route('/changes.json')
@public
@cross_origin()
def translation_changes():
    try:
        r = requests.get("http://www.golabz.eu/rest/labs/retrieve.json")
        r.raise_for_status()
        labs = r.json()
    except:
        return "Error accessing http://www.golabz.eu/rest/labs/retrieve.json", 500

    from appcomposer.translator.tasks import GOLAB_REPO
    repository_apps = db.session.query(RepositoryApp).filter_by(repository=GOLAB_REPO).filter(RepositoryApp.app_link.like('http://www.golabz.eu/lab%'), or_(RepositoryApp.translation_percent != None, RepositoryApp.original_translations != None)).all()
    automatic_urls = {}
    for translated_app in db.session.query(TranslatedApp).filter(TranslatedApp.url.in_([ repo_app.url for repo_app in repository_apps ])).all():
        automatic_urls[translated_app.url] = translated_app.translation_url.automatic

    repository_apps_by_external_id = defaultdict(list) # {
        # id: [ repository_app1, repository_app2, repository_app3 ... ]
    # }
    for repository_app in repository_apps:
        external_id = repository_app.external_id.split('-')[0]
        repository_apps_by_external_id[external_id].append(repository_app)

    threshold = request.args.get('threshold', 100 * LANGUAGE_THRESHOLD)
    try:
        threshold = float(threshold)
    except (ValueError, TypeError):
        threshold = 100 * LANGUAGE_THRESHOLD
    threshold = threshold / 100.0

    show_names = request.args.get('show_names', 'false').lower() == 'true'
    show_urls = request.args.get('show_urls', 'false').lower() == 'true'
    show_total = request.args.get('show_total', 'false').lower() == 'true'

    changes = {
        # If there is a change (removal, addition), it lists it like this:
        # identifier: [ lang1, lang2, lang3 ] 
    }
    total_changes = {
        # If there is an addition, it lists it like this:
        # identifier: {
        #     'additions' : [lang1, lang2]
        #     'subtractions' : [lang3, lang4]
        # }
    }
    visible_languages = [ key.split('_')[0] for key in obtain_languages().keys() ]
    for lab in labs:
        external_id = lab.get('id')
        appcomposer_languages = set()
        for repo_app in repository_apps_by_external_id.get(external_id, []):
            # If it is not automatic we should not count it (only the original translations)
            if automatic_urls.get(repo_app.url, True):
                translation_percent = json.loads(repo_app.translation_percent or "{}")
                for lang, value in translation_percent.items():
                    if value >= threshold:
                        # lang should be 'en'; not 'en_ALL_ALL'
                        lang = lang.split('_')[0]
                        appcomposer_languages.add(lang)

            for lang in (repo_app.original_translations or '').split(','):
                if lang:
                    lang = lang.split('_')[0]
                    if lang in visible_languages:
                        appcomposer_languages.add(lang)

        lab_languages = lab.get('lab_languages', [])
        golabz_languages = set()
        for language in lab_languages:
            # If the language is in WRONG_LANGUAGES, take it; otherwise keep it
            language = WRONG_LANGUAGES.get(language, language)
            if language in LANGUAGES_PER_NAME:
                lang_code = LANGUAGES_PER_NAME[language]
                golabz_languages.add(lang_code)

        # If there are changes and there are appcomposer languages
        if len(appcomposer_languages) > 0:
            additions = appcomposer_languages - golabz_languages
            subtractions = golabz_languages - appcomposer_languages
            if subtractions or additions:
                identifier = external_id
                if show_urls:
                    repo_apps = repository_apps_by_external_id.get(external_id, [])
                    if repo_apps:
                        identifier = repo_apps[0].app_link

                elif show_names:
                    repo_apps = repository_apps_by_external_id.get(external_id, [])
                    if repo_apps:
                        identifier = repo_apps[0].name
                
                total_changes[identifier] = {}
                if subtractions:
                    total_changes[identifier]['subtractions'] = list(subtractions)
                if additions:
                    total_changes[identifier]['additions'] = list(additions)
                changes[identifier] = []
                for lang_code in appcomposer_languages:
                    display_name = LANGUAGE_NAMES_PER_CODE.get(lang_code, lang_code)
                    display_name = WRONG_LANGUAGES_PER_CORRECT_NAME.get(display_name, [ display_name ])[0]
                    changes[identifier].append(display_name)
                changes[identifier] = sort_languages(changes[identifier])
    response = dict(changes=changes)
    if show_total:
        response['total_changes'] = total_changes
    return jsonify(**response)

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

@translator_dev_blueprint.route('/upload/', methods = ('GET', 'POST'))
@requires_golab_login
def translation_upload():
    default_language = guess_default_language()
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

@translator_dev_blueprint.route('/')
@public
def translations():
    return render_template("translator/translations.html")

@translator_dev_blueprint.route('/users')
def translation_users_old():
    return redirect(url_for('translator_stats.translation_users'))

@translator_dev_blueprint.route('/sync/', methods = ['GET', 'POST'])
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
        latest_id = latest_synchronizations[0]['id']
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


@translator_dev_blueprint.route('/sync/debug/')
def sync_debug():
    # Just in case the debug value changes during the load of modules
    if not current_app.debug:
        return "Not in debug mode!"

    now = datetime.datetime.utcnow()
    t0 = time.time()
    from appcomposer.translator.translation_listing import synchronize_apps_no_cache
    synchronize_apps_no_cache("sync debug")
    tf = time.time()
    return "<html><body>synchronization process finished (%.2f seconds): %s </body></html>" % (tf - t0, now)

@translator_dev_blueprint.route('/urls/')
@public
def translations_urls():
    urls = {}
    for db_url in db.session.query(TranslationUrl).options(joinedload('bundles')):
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

@translator_dev_blueprint.route('/apps/')
@public
def translations_apps():
    # Takes 1ms to load these two files. And putting it here is better for being able to change the code dynamically
    apps_angular_code = open(os.path.join(SITE_ROOT, "appcomposer/templates/translator/apps_angular_js.js")).read()
    apps_angular_html = open(os.path.join(SITE_ROOT, "appcomposer/templates/translator/apps_angular_html.html")).read()

    return render_template("translator/translations_apps2.html", angular_js = apps_angular_code, angular_html = apps_angular_html, NAMES = NAMES)

@translator_dev_blueprint.route('/apps/<path:app_url>')
@public
def translations_apps_filtered(app_url):
    app = db.session.query(TranslatedApp).filter_by(url = app_url).first()
    if app is None:
        return render_template("translator/error.html", message = "App does not exist"), 404

    # Takes 1ms to load these two files. And putting it here is better for being able to change the code dynamically
    apps_angular_code = open(os.path.join(SITE_ROOT, "appcomposer/templates/translator/apps_angular_js.js")).read()
    apps_angular_html = open(os.path.join(SITE_ROOT, "appcomposer/templates/translator/apps_angular_html.html")).read()

    return render_template("translator/translations_apps2.html", angular_js = apps_angular_code, angular_html = apps_angular_html, NAMES = NAMES, app_url = app_url)

@translator_dev_blueprint.route('/apps/revisions/<lang>/<target>/<path:app_url>')
@public
def translations_revisions(lang, target, app_url):
    translation_app = db.session.query(TranslatedApp).filter_by(url = app_url).options(joinedload('translation_url')).first()
    if translation_app is None:
        return render_template("translator/error.html", message = "App does not exist"), 404

    translation_url = translation_app.translation_url
    translation_url_url = translation_url.url

    bundle = db.session.query(TranslationBundle).filter_by(translation_url = translation_url, language = lang, target = target).first()
    if bundle is None:
        return render_template("translator/error.html", message = "App found, but no translation for that language or target"), 404

    db_messages = db.session.query(TranslationMessageHistory).filter_by(bundle = bundle).options(joinedload('user')).order_by('-datetime').all()

    messages = {
        # key: {
        #    'key' : key,
        #    'revisions' : {
        #         'id': <id>,
        #         'parent_id': <parent_id>,
        #         'date': datetime,
        #         'user': {'display_name': "...", 'email': "..."},
        #         'value': value,
        #         'from_default' : true/false

        #         'from_developer' : true/false
        #    } }
    }

    past_collaborators = {
        # email: display_name
    }

    for message in db_messages:
        if message.key not in messages:
            messages[message.key] = {
                'key' : message.key,
                'revisions' : []
            }

        messages[message.key]['revisions'].append({
            'id' : message.id,
            'parent_id' : message.parent_translation_id,
            'date' : message.datetime,
            'user' : {
                'display_name' : message.user.display_name,
                'email' : message.user.email,
            },
            'value' : message.value,
            'from_default': message.taken_from_default,
            'from_developer': message.from_developer,
            'tool_id': message.tool_id,
        })
        past_collaborators[message.user.email] = message.user.display_name

    collaborators = {
        # email: display_name
    }
    db_active_messages = db.session.query(ActiveTranslationMessage).filter_by(bundle = bundle).options(joinedload('history.user'), joinedload('history')).order_by('-ActiveTranslationMessages.datetime').limit(10000) # when using .all(), there is hundreds of queries when commit() is run
    active_messages = []
    active_values = [ am.value for am in db_active_messages ]

    suggestions = {}

    #
    # translate_texts might call db.session.remove!
    #
    for human_key, suggested_values in translate_texts(active_values, 'en', lang.split('_')[0]).iteritems():
        suggestions[human_key] = ' / '.join([ key for key, value in sorted(suggested_values.items(), lambda (x1, x2), (y1 ,y2): cmp(x2, y2), reverse = True) ])

    db.session.remove() # Force remove so we start with a new database connection after translations

    translation_url = db.session.query(TranslationUrl).filter_by(url = translation_url_url).first()
    bundle = db.session.query(TranslationBundle).filter_by(translation_url = translation_url, language = lang, target = target).first()
    db_active_messages = db.session.query(ActiveTranslationMessage).filter_by(bundle = bundle).options(joinedload('history.user'), joinedload('history')).order_by('-ActiveTranslationMessages.datetime').limit(10000) # when using .all(), there is hundreds of queries when commit() is run
    for active_message in db_active_messages:
        active_messages.append({
            'key': active_message.key,
            'value' : active_message.value,
            'datetime' : active_message.datetime,
            'suggestions' : suggestions.get(active_message.value, {}),
            'user' : {
                'display_name' : active_message.history.user.display_name,
                'email' : active_message.history.user.email,
            },
            'from_default': active_message.taken_from_default,
            'from_developer': active_message.from_developer,
        })
        collaborators[active_message.history.user.email] = active_message.history.user.display_name

    for collaborator in collaborators:
        past_collaborators.pop(collaborator, None)

    english_bundle = db.session.query(TranslationBundle).filter_by(translation_url = translation_url, language = 'en_ALL', target = 'ALL').first()
    english_messages = {
        # key: english_value
    }
    if english_bundle is not None:
        english_translations = db.session.query(ActiveTranslationMessage.key, ActiveTranslationMessage.value).filter_by(bundle = english_bundle).all()
        for key, value in english_translations:
            english_messages[key] = value
    
    for am in active_messages:
        key = am['key']
        if key not in english_messages:
            english_messages[key] = "(No English translation available)"

    supported_languages = db.session.query(TranslationBundle.language, TranslationBundle.target).filter_by(translation_url = translation_url).all()

    return render_template("translator/revisions.html", url = app_url, lang = lang, target = target, messages = messages, active_messages = active_messages, collaborators = collaborators, past_collaborators = past_collaborators, supported_languages = supported_languages, app_url = app_url, english_messages = english_messages)

@translator_dev_blueprint.route('/apps/failing/')
@public
def apps_failing():
    return redirect(url_for('translator_stats.apps_failing'))

@translator_dev_blueprint.route('/apps/apps.json')
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

    for app in db.session.query(TranslatedApp).options(joinedload('translation_url.bundles')):
        if requested_app_url is not None and requested_app_url != app.url:
            continue

        if app.translation_url is not None and max_date_per_translation_url_id.get(app.translation_url_id) is None:
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

@translator_dev_blueprint.route('/apps/<lang>/<target>/<path:app_url>')
@public
def translations_app_xml(lang, target, app_url):
    return _translate_app(lang, target, app_url, output_format = FORMAT_OPENSOCIAL)

@translator_dev_blueprint.route('/apps/all.zip')
@public
def translations_app_all_zip():
    return _translate_app_all_zip(output_format = FORMAT_OPENSOCIAL)

@translator_dev_blueprint.route('/apps/all/<path:app_url>')
@public
def translations_app_url_zip(app_url):
    return _translations_app_url_zip(app_url, output_format = FORMAT_OPENSOCIAL)

@translator_dev_blueprint.route('/urls/<lang>/<target>/<path:url>')
@public
def translations_url_xml(lang, target, url):
    return _translate_url(lang, target, url, output_format = FORMAT_OPENSOCIAL)

# 
# Generic links
# 

@translator_dev_blueprint.route('/apps/<format_key>/<lang>/<target>/<path:app_url>')
@public
def translations_app_format(format_key, lang, target, app_url):
    if format_key not in NAMES:
        return "Invalid format", 404
    return _translate_app(lang, target, app_url, output_format = format_key)

@translator_dev_blueprint.route('/apps/<format_key>/all.zip')
@public
def translations_app_all_format_zip(format_key):
    if format_key not in NAMES:
        return "Invalid format", 404
    return _translate_app_all_zip(output_format = format_key)

@translator_dev_blueprint.route('/apps/<format_key>/<path:app_url>')
@public
def translations_app_url_format_zip(format_key, app_url):
    if format_key not in NAMES:
        return "Invalid format", 404
    return _translations_app_url_zip(app_url, output_format = format_key)

@translator_dev_blueprint.route('/urls/<format_key>/<lang>/<target>/<path:url>')
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
            zf.writestr('%s_%s.%s' % (bundle.language, bundle.target, extension), xml_contents.encode('utf8'))
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

@translator_dev_blueprint.route('/mongodb/')
@public
def translations_mongodb():
    collections = {}
    contents = retrieve_mongodb_contents()
    for collection, collection_contents in contents.iteritems():
        collections[collection] = json.dumps(collection_contents, indent = 4)
    return render_template("translator/mongodb.html", collections = collections)

@translator_dev_blueprint.route('/mongodb/apps/')
@public
def translations_mongodb_apps():
    apps = retrieve_mongodb_apps()
    return render_template("translator/mongodb_listing.html", apps = apps, title = "Apps", xml_method = '.translations_mongodb_apps_xml')

@translator_dev_blueprint.route('/mongodb/urls/')
@public
def translations_mongodb_urls():
    apps = retrieve_mongodb_urls()
    return render_template("translator/mongodb_listing.html", apps = apps, title = "URLs", xml_method = '.translations_mongodb_urls_xml')

@translator_dev_blueprint.route('/mongodb/apps/<lang>/<target>/<path:url>')
@public
def translations_mongodb_apps_xml(lang, target, url):
    data = retrieve_mongodb_app(lang, target, url)
    if data is not None:
        resp = make_response(messages_to_xml(json.loads(data)))
        resp.content_type = 'application/xml'
        return resp

    return "Not found", 404

@translator_dev_blueprint.route('/mongodb/urls/<lang>/<target>/<path:url>')
@public
def translations_mongodb_urls_xml(lang, target, url):
    data = retrieve_mongodb_translation_url(lang, target, url)
    if data is not None:
        resp = make_response(messages_to_xml(json.loads(data)))
        resp.content_type = 'application/xml'
        return resp

    return "Not found", 404


