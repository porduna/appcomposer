"""
New translator
"""

import json
import xml.etree.ElementTree as ET

from sqlalchemy.orm import joinedload_all

from flask import Blueprint, make_response, render_template, request, flash
from flask.ext.wtf import Form
from flask.ext.wtf.file import FileField
from flask.ext.admin.form import Select2Field
from wtforms.fields.html5 import URLField
from wtforms.validators import url, required

from appcomposer import db
from appcomposer.models import TranslatedApp, TranslationUrl, TranslationBundle
from appcomposer.login import requires_login, current_user
from appcomposer.translator.languages import obtain_groups, obtain_languages
from appcomposer.translator.utils import extract_local_translations_url, extract_messages_from_translation
from appcomposer.translator.ops import add_full_translation_to_app

translator_blueprint = Blueprint('translator', __name__)

#
# Use @public to mark that a method is intentionally public
# 
def public(func): return func

@translator_blueprint.route('/')
@requires_login
def translator_index():
    return "Hi there, this is the new translator"

@translator_blueprint.route('/translate')
@requires_login
def translate():
    return "Now I should translate something"

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
@requires_login
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
            form.url.errors = [unicode(e)]
            errors = True

        xml_contents = form.opensocial_xml.data.read()
        try:
            translated_messages = extract_messages_from_translation(xml_contents)
        except Exception as e:
            form.opensocial_xml.errors = [unicode(e)]
            errors = True
        
        if not errors:
            language = form.language.data
            target = form.target.data
            add_full_translation_to_app(current_user(), app_url, translation_url, language, target, translated_messages, original_messages)
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
                    'target' : bundle.target,
                    'lang' : bundle.language,
                })
        else:
            # TODO: invalid state
            pass
    return render_template("translator/translations_apps.html", apps = apps)

# 
# TODO:
# 1. Zip file for all the translations for a given URL
# 2. Zip file for all the translations
# 

@translator_blueprint.route('/translations/apps/<lang>/<target>/<path:app_url>')
@public
def translations_app_xml(lang, target, app_url):
    translation_app = db.session.query(TranslatedApp).filter_by(url = app_url).first()
    if translation_app is None:
        return "Translation App not found in the database", 404

    return translations_url_xml(lang, target, translation_app.translation_url.url)

@translator_blueprint.route('/translations/urls/<lang>/<target>/<path:url>')
@public
def translations_url_xml(lang, target, url):
    translation_url = db.session.query(TranslationUrl).filter_by(url = url).first()
    if translation_url is None:
        return "Translation URL not found in the database", 404

    bundle = db.session.query(TranslationBundle).filter_by(translation_url = translation_url, language = lang, target = target).first()
    if bundle is None:
        return "Translation URL found, but no translation for that language or target"

    xml_bundle = ET.Element("messagebundle")
    for message in bundle.active_messages:  
        xml_msg = ET.SubElement(xml_bundle, 'msg')
        xml_msg.attrib['name'] = message.key
        xml_msg.text = message.value

    resp = make_response(ET.tostring(xml_bundle, encoding = 'utf8'))
    resp.content_type = 'application/xml'
    return resp
