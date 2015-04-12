"""
New translator
"""

import os
import json
import zipfile
import StringIO
import traceback

from collections import OrderedDict

from sqlalchemy.orm import joinedload_all

from flask import Blueprint, make_response, render_template, request, flash, redirect, url_for, jsonify
from flask.ext.wtf import Form
from flask.ext.wtf.file import FileField
from flask.ext.admin.form import Select2Field
from wtforms.fields.html5 import URLField
from wtforms.validators import url, required

from appcomposer import db
from appcomposer.models import TranslatedApp, TranslationUrl, TranslationBundle, RepositoryApp
from appcomposer.login import requires_golab_login, current_golab_user
from appcomposer.translator.languages import obtain_groups, obtain_languages
from appcomposer.translator.utils import extract_local_translations_url, extract_messages_from_translation
from appcomposer.translator.ops import add_full_translation_to_app, retrieve_stored, retrieve_suggestions
from appcomposer.translator.utils import bundle_to_xml, url_to_filename, messages_to_xml
from appcomposer.translator.mongodb_pusher import retrieve_mongodb_contents

translator_blueprint = Blueprint('translator', __name__)

#
# Use @public to mark that a method is intentionally public
# 
def public(func): return func

@translator_blueprint.route('/')
@requires_golab_login
def translator_index():
    return render_template("translator/index.html")

@translator_blueprint.route("/api/apps/<path:appurl>/bundles/<targetlang>", methods=["POST"])
@requires_golab_login
def create_language(appurl, targetlang):
    # TODO: this method is not needed
    return jsonify(**{"result": "ok"})

@translator_blueprint.route("/api/apps/<path:appurl>/bundles/<targetlang>/<targetgroup>", methods=["POST"])
@requires_golab_login
def create_group(appurl, targetlang, targetgroup):
    # TODO: this method is not needed
    return jsonify(**{"result": "ok"})


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

@translator_blueprint.route('/api/translations')
@public
def api_translations():
    # XXX: Removed: author (not the original one), app_type (always OpenSocial). 
    # XXX: original_languages does not have target (nobody has it)
    # XXX: app_golabz_page renamed as app_link
    # XXX: response is { 'applications' : [] } (and not [] directly )

    applications = []
    for repo_app in db.session.query(RepositoryApp).filter_by(translatable = True).all():
        original_languages = repo_app.original_translations.split(',')
        if original_languages == "":
            original_languages = []
        original_languages_simplified = [ lang.split('_')[0] for lang in original_languages ]
        try:
            translated_languages = json.loads(repo_app.translation_percent) or {}
        except ValueError:
            translated_languages = {}

        applications.append({
            'original_languages' : original_languages,
            'original_languages_simplified' : original_languages_simplified,
            'translated_languages' : translated_languages,
            'source' : repo_app.repository,
            'id' : repo_app.external_id,
            'description': repo_app.description,
            'app_url' : repo_app.url,
            'app_thumb' : repo_app.app_thumb,
            'app_link' : repo_app.app_link,
            'app_image' : repo_app.app_image,
        })
    
    return jsonify(applications = applications) 

@translator_blueprint.route('/api/info/languages')
@public
def api_languages():
    ordered_dict = OrderedDict()
    languages = list(obtain_languages().iteritems())
    languages.sort(lambda x1, x2 : cmp(x1[1], x2[1]))
    for lang_code, lang_name in languages:
        ordered_dict[lang_code] = lang_name
    return jsonify(**ordered_dict)

@translator_blueprint.route('/api/info/groups')
@public
def api_groups():
    return jsonify(**obtain_groups())

@translator_blueprint.route("/api/apps/<path:appurl>/bundles/<targetlang>/<targetgroup>/updateMessage", methods=["GET", "PUT"])
@requires_golab_login
def bundle_update(appurl, targetlang, targetgroup):
    # TODO: implement this code
    key = request.values.get("key")
    value = request.values.get("value")

    if key is None or value is None:
        return jsonify(**{"result":"error"})

    return jsonify(**{"result": "success"})

@translator_blueprint.route('/translate')
@translator_blueprint.route('/api/apps/')
@requires_golab_login
def api_translate():
    app_url = request.args.get('app_url')
    language = request.args.get('lang')
    target = request.args.get('target')

    errors = []
    if not app_url:
        errors.append("'app_url' argument missing")
    if not language:
        errors.append("'lang' argument missing")
    if not target:
        errors.append("'target' argument missing")
    if errors:
        return '; '.join(errors), 400

    translation_url, original_messages = extract_local_translations_url(app_url)
    translation = {}

    stored_translations, from_developer = retrieve_stored(translation_url, language, target)
    suggestions = retrieve_suggestions(original_messages, language, target, stored_translations)
    for key, value in original_messages.iteritems():
        stored = stored_translations.get(key, {})
        translation[key] = {
            'source' : value,
            'target' : stored.get('value'),
            'from_default' : stored.get('from_default', False),
            'suggestions' : suggestions.get(key, []),
            'can_edit' : not from_developer
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

    response = {
        'url' : app_url,
        'app_thumb' : app_thumb,
        'name' : name,
        'translation' : translation,
    }


    if False:
        response = json.dumps(response, indent = 4)
        return "<html><body>%s</body></html>" % response
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

@translator_blueprint.route('/translations/upload/', methods = ('GET', 'POST'))
@requires_golab_login
def translation_upload():
    best_match = request.accept_languages.best_match([ lang_code.split('_')[0] for lang_code in LANGUAGES ])
    default_language = None
    if best_match is not None:
        if best_match in LANGUAGES:
            default_language = best_match
        else:
            lang_codes = [ lang_code for lang_code in LANGUAGES if lang_code.startswith('%s_' % best_match) ]
            if lang_codes:
                default_language = lang_codes[0]

    if default_language:
        form = UploadForm(language = default_language)
    else:
        form = UploadForm()

    if form.validate_on_submit():
        errors = False
        app_url = form.url.data

        try:
            translation_url, original_messages = extract_local_translations_url(app_url)
        except Exception as e:
            traceback.print_exc()
            form.url.errors = [unicode(e)]
            errors = True

        xml_contents = form.opensocial_xml.data.read()
        if isinstance(xml_contents, str):
            xml_contents = unicode(xml_contents, 'utf8')
        try:
            translated_messages = extract_messages_from_translation(xml_contents)
        except Exception as e:
            traceback.print_exc()
            form.opensocial_xml.errors = [unicode(e)]
            errors = True
        
        if not errors:
            language = form.language.data
            target = form.target.data
            add_full_translation_to_app(current_golab_user(), app_url, translation_url, language, target, translated_messages, original_messages, from_developer = False)
            flash("Contents successfully added")

    return render_template('translator/translations_upload.html', form=form)

@translator_blueprint.route('/translations/')
@public
def translations():
    return render_template("translator/translations.html")

@translator_blueprint.route('/translations/urls/')
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

@translator_blueprint.route('/translations/apps/')
@public
def translations_apps():
    apps = {}
    for app in db.session.query(TranslatedApp).options(joinedload_all('translation_url.bundles')):
        apps[app.url] = []
        if app.translation_url is not None:
            for bundle in app.translation_url.bundles:
                apps[app.url].append({
                    'from_developer' : bundle.from_developer,
                    'target' : bundle.target,
                    'lang' : bundle.language,
                })
        else:
            # TODO: invalid state
            pass
    return render_template("translator/translations_apps.html", apps = apps)

@translator_blueprint.route('/translations/apps/<lang>/<target>/<path:app_url>')
@public
def translations_app_xml(lang, target, app_url):
    translation_app = db.session.query(TranslatedApp).filter_by(url = app_url).first()
    if translation_app is None:
        return "Translation App not found in the database", 404

    return translations_url_xml(lang, target, translation_app.translation_url.url)

@translator_blueprint.route('/translations/apps/all.zip')
@public
def translations_app_all_zip():
    translated_apps = db.session.query(TranslatedApp).filter_by().all()
    sio = StringIO.StringIO()
    zf = zipfile.ZipFile(sio, 'w')
    for translated_app in translated_apps:
        translated_app_filename = url_to_filename(translated_app.url)
        if translated_app.translation_url:
            for bundle in translated_app.translation_url.bundles:
                xml_contents = bundle_to_xml(bundle)
                zf.writestr('%s_%s.xml' % (os.path.join(translated_app_filename, bundle.language), bundle.target), xml_contents)
    zf.close()

    resp = make_response(sio.getvalue())
    resp.content_type = 'application/zip'
    return resp

@translator_blueprint.route('/translations/apps/all/<path:app_url>')
@public
def translations_app_url_zip(app_url):
    translated_app = db.session.query(TranslatedApp).filter_by(url = app_url).first()
    if translated_app is None:
        return "Translation App not found in the database", 404
   
    sio = StringIO.StringIO()
    zf = zipfile.ZipFile(sio, 'w')
    translated_app_filename = url_to_filename(translated_app.url)
    if translated_app.translation_url:
        for bundle in translated_app.translation_url.bundles:
            xml_contents = bundle_to_xml(bundle)
            zf.writestr('%s_%s.xml' % (bundle.language, bundle.target), xml_contents)
    zf.close()

    resp = make_response(sio.getvalue())
    resp.content_type = 'application/zip'
    resp.headers['Content-Disposition'] = 'attachment;filename=%s.zip' % translated_app_filename
    return resp


@translator_blueprint.route('/translations/urls/<lang>/<target>/<path:url>')
@public
def translations_url_xml(lang, target, url):
    translation_url = db.session.query(TranslationUrl).filter_by(url = url).first()
    if translation_url is None:
        return "Translation URL not found in the database", 404

    bundle = db.session.query(TranslationBundle).filter_by(translation_url = translation_url, language = lang, target = target).first()
    if bundle is None:
        return "Translation URL found, but no translation for that language or target"

    messages_xml = bundle_to_xml(bundle)
    resp = make_response(messages_xml)
    resp.content_type = 'application/xml'
    return resp

@translator_blueprint.route('/translations/mongodb/')
@public
def translations_mongodb():
    collections = {}
    contents = retrieve_mongodb_contents()
    for collection, collection_contents in contents.iteritems():
        collections[collection] = json.dumps(collection_contents, indent = 4)
    return render_template("translator/mongodb.html", collections = collections)

@translator_blueprint.route('/translations/mongodb/apps/')
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

@translator_blueprint.route('/translations/mongodb/urls/')
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

    return render_template("translator/mongodb_listing.html", apps = apps, title = "URLs", xml_method = '.translations_mongodb_apps_xml')

@translator_blueprint.route('/translations/mongodb/apps/<lang>/<target>/<path:url>')
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

@translator_blueprint.route('/translations/mongodb/urls/<lang>/<target>/<path:url>')
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

