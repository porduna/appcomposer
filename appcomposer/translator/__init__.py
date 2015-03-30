"""
New translator
"""

import json
import xml.etree.ElementTree as ET

from sqlalchemy.orm import joinedload_all

from flask import Blueprint, make_response, render_template

from appcomposer import db
from appcomposer.models import TranslatedApp, TranslationUrl
from appcomposer.login import requires_login

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

@translator_blueprint.route('/translations/upload/')
@requires_login
def translation_upload():
    pass

@translator_blueprint.route('/translations/')
@public
def translations():
    return render_template("translator/translations.html")

@translator_blueprint.route('/translations/urls/')
@public
def translations_urls():
    urls = {}
    for url in db.session.query(TranslationUrl).options(joinedload_all('bundles')):
        urls[url] = []
        for bundle in url.bundles:
            urls[url].append({
                'target' : bundle.target,
                'lang' : bundle.language,
            })
    return render_template("translator/translations_urls.html", urls = urls)

@translator_blueprint.route('/translations/apps/')
@public
def translations_apps():
    apps = {}
    for app in db.session.query(TranslatedApp).options(joinedload_all('translation_url.bundles')):
        apps[app] = []
        for bundle in app.translation_url.bundles:
            apps[app].append({
                'target' : bundle.target,
                'lang' : bundle.language,
            })
    return render_template("translator/translations_apps.html", apps = apps)

@translator_blueprint.route('/translations/apps/<lang>/<target>/<path:url>')
@public
def translations_app_xml(lang, target, app_url):
    translation_app = db.session.query(TranslationApp).filter_by(url = url).first()
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

    resp = make_response(ET.dump(xml_bundle))
    resp.content_type = 'application/xml'
    return resp
