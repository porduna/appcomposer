import json
import traceback

from flask import Blueprint, make_response, render_template, request, redirect, url_for
from flask_cors import cross_origin

from appcomposer.db import db
from appcomposer.models import RepositoryApp
from appcomposer.login import requires_golab_login
from appcomposer.languages import obtain_groups, obtain_languages

from appcomposer.utils import public
from appcomposer.languages import LANGUAGES, LANGUAGE_THRESHOLD, sort_languages

import flask_cors.core as cors_core
cors_core.debugLog = lambda *args, **kwargs : None

translator_blueprint = Blueprint('translator', __name__, static_folder = '../../translator3/dist/', static_url_path = '/web')

@translator_blueprint.route('/')
@requires_golab_login
def translator_index():
    return redirect(url_for('.static', filename='index.html'))

@translator_blueprint.route('/select')
@public
def select_translations():
    app_url = request.args.get('app_url')
    language = request.args.get('lang')
    target = request.args.get('target')

    if app_url and language and target:
        return redirect(url_for('translator_api.api_translate', app_url = app_url, language = language, target = target))

    targets = obtain_groups()
    languages = list(obtain_languages().iteritems())
    languages.sort(lambda x1, x2 : cmp(x1[1], x2[1]))
    return render_template("translator/select_translations.html", targets = targets, languages = languages)

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
            if percent >= LANGUAGE_THRESHOLD:
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
        str_translations = u', '.join(sort_languages(human_translations))

        if str_translations and link:
            resp = make_response(render_template("translator/lib.js", translations = sort_languages(human_translations), link = link))
        else:
            resp = make_response("// App found and transtable, but no translation found")
        resp.content_type = 'application/javascript'
        return resp
    except Exception as e:
        traceback.print_exc()
        resp = make_response("""// Error: %s """ % repr(e))
        resp.content_type = 'application/javascript'
        return resp



