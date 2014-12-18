import os
from flask import render_template, jsonify, json, Response, current_app, send_file, render_template_string
from werkzeug.exceptions import NotFound
from appcomposer.babel import gettext, get_domain
from appcomposer.composers.translate2 import translate2_blueprint
from appcomposer.composers.translate2.translation_listing import retrieve_translations
from appcomposer.application import app as flask_app




def serve_ngapp(appname, path):
    """
    Seves the specified ngapp.
    Ngapps are expected to be in the ngapps folder.

    Different files will be served depending on whether we are in DEVELOPMENT or in DISTRIBUTION mode.

    *** DEVELOPMENT MODE ***
    The files to be served will be a merge from the app folder (which will be tried first) and the .tmp
    folder. If it is a bower_components dependency, it will also be served.
    The index.html file is the only file to be rendered as a Jinja2 template.

    *** DISTRIBUTION MODE ***
    The files to be served will only be obtained from the dist folder. Only the index.html file will be
    rendered as a Jinja2 template. All other files will be served statically. In production, the
    WebServer could thus be configured to serve any of these (except index.html, which will be
    rendered through Jinja).

    :param appname: Name of the app to serve. Its folder should be within the
    ngapps folder.
    :ptype appname: str

    :param path: The specific path to serve.
    :ptype path: str

    :return:
    """
    # We first need to know whether we are in development or in distribution mode. We will check through
    # config and environment variables.
    dev_mode = flask_app.config.get("NGAPPS_DEV_MODE", False) or int(os.environ.get('NGAPPS_DEV_MODE', False))

    # Calculate some base paths we will need
    root_path = os.path.join(current_app.root_path, "ngapps", appname)

    if dev_mode:

        if path.startswith("bower_components/"):
            uri = os.path.join(root_path, path)
            return send_file(uri)

        first_uri = os.path.join(root_path, "app", path)

        # Recognize index.html
        if path == "index.html":
            # return render_template_string(open(first_uri).read().decode('utf-8'),
            #                               config=current_app.config)
            translations = get_domain().get_translations()._catalog
            config = current_app.config
            contents = open(first_uri).read().decode('utf-8')
            return render_template_string(contents, config=config, translations=translations)

        # Check wether the first uri (file in app) exists. Otherwise we need to search
        # in .tmp
        if os.path.isfile(first_uri):
            return send_file(first_uri)

        second_uri = os.path.join(root_path, ".tmp", path)

        if os.path.isfile(second_uri):
            return send_file(second_uri)

        # If not found we throw NotFound
        raise NotFound()

    else:
        # DISTRIBUTION mode. We serve everything from the dist folder.

        only_uri = os.path.join(root_path, "app", "dist")

        if path == "index.html":
            translations = get_domain().get_translations()._catalog
            return render_template_string(open(only_uri).read().decode('utf-8'),
                                          config=current_app.config, translations=translations)

        if os.path.isfile(only_uri):
            return send_file(only_uri)

        # If not found we throw NotFound
        raise NotFound()



@translate2_blueprint.route('/', defaults={'path': 'index.html'})
@translate2_blueprint.route('/<path:path>')
def index(path):
    return serve_ngapp("translate2", path)

@translate2_blueprint.route("/translations")
def translations():
    """
    Retrieves from a local cache a subset of the app repository
    which is filtered to include only apps of interest to the
    translator (translatable apps) and extended with certain
    information (such as languages it has been translated to).

    :return: Response containing JSON with the format:
    [{
        'original_languages': ['es_ES_ALL'],
        'original_languages_simplified': ['es', 'en'],
        'translated_languages': {'es_ES_ALL': 0.8},
        'source: 'golabz', // or external
        'id': 190, 'author': 'admin', 'description': 'This app...',
        'app_url': '...',
        app_type: "OpenSocial gadget",
        app_image: "http://www.golabz.eu/sites/default/files/images/app/app-image/statistics.png",
        app_thumb: "http://www.golabz.eu/sites/default/files/styles/overview/public/images/app/app-image/statistics.png",
        app_golabz_page: "http://www.golabz.eu/apps/action-statistics"
    }]
    """

    data = json.dumps(retrieve_translations())
    return Response(data, mimetype="application/json")

@translate2_blueprint.route("/translations/bundle/<path:appurl>/<srclang>/<srcgroup>/<targetlang>/<targetgroup>")
def bundle(appurl, srclang, srcgroup, targetlang, targetgroup):
    """
    Retrieves information about a specific translation (bundle).
    :param appurl:
    :param srclang:
    :param srcgroup:
    :param targetlang:
    :param targetgroup:
    :return:
    """
    data = {
        "url": "http://www.applications.com/app.xml",
        "app_thumb": "http://www.golabz.eu/sites/default/files/styles/overview/public/images/app/app-image/statistics.png",
        "name": "My Application",
        "translation": {
            "ht_hello_world": {
                "can_edit": True,
                "source": "Hello world!",
                "target": "Hola mundo!",
                "suggestions": [
                    {
                        "target": "hola mundo",
                        "weight": 0.9
                    },
                    {
                        "target": "hola!",
                        "weight": 0.8
                    }
                ]
            }
        }
    }

    return jsonify(**data)

@translate2_blueprint.route("/translations/apps/<path:appurl>")
def app(appurl):
    """
    Retrieves information for a specific Application, identified by its App URL.
    That information contains information such as existing translations, their
    translators, etc.
    :param appurl: The URL of the App
    :return:
    """

    data = {
        "url": "http://www.applications.com/app.xml",
        "app_thumb": "http://www.golabz.eu/sites/default/files/styles/overview/public/images/app/app-image/statistics.png",
        "name": "My Application",
        "desc": "This is only a test application which does not really exist.",
        "translations": {
            "all_ALL": {
                "name": "DEFAULT",
                "targets": {
                    "ALL": {
                        "modified_date": "2014-02-24",
                        "created_date": "2014-01-12",
                        "name": "ALL",
                        "translated": 21,
                        "items": 31
                    },
                    "12-14": {
                        "modified_date": "2014-02-24",
                        "created_date": "2014-01-12",
                        "name": "Adolescents (12-14)",
                        "translated": 12,
                        "items": 31
                    }
                }
            },
            "en_ALL": {
                "name": "English",
                "targets": {
                    "ALL": {
                        "modified_date": "2014-02-24",
                        "created_date": "2014-01-12",
                        "name": "ALL",
                        "translated": 31,
                        "items": 31
                    }
                }
            }
        }
    }

    return jsonify(**data)