import json
from flask import jsonify, Response, request
from flask.ext.cors import cross_origin
from appcomposer.composers.translate2.translation_listing import retrieve_translations
from appcomposer.composers.translate3 import translate3_blueprint


@translate3_blueprint.route("/")
def api_():
    return "Translate 3 index"



@translate3_blueprint.route("/api/translations")
@cross_origin()
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

@translate3_blueprint.route("/api/apps/<path:appurl>/bundles/<targetlang>/<targetgroup>/translationInfo/<srclang>/<srcgroup>")
@cross_origin()
def bundle(appurl, targetlang, targetgroup, srclang, srcgroup):
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
        "app_thumb": "http://www.golabz.eu/sites/default/files/styles/overview/public/images/app/app-image/Action%20Statistics_no_title.png",
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
            },
            "ht_whatever": {
                "can_edit": True,
                "source": "Whatever!",
                "target": "Cualquier cosa",
                "suggestions": [
                    {
                        "target": "cualquier",
                        "weight": 0.9
                    },
                    {
                        "target": "cualquier cosa!",
                        "weight": 0.8
                    }
                ]
            }
        }
    }

    return jsonify(**data)

@translate3_blueprint.route("/api/info/languages")
@cross_origin()
def info_languages():
    """
    Retrieves the dictionary of all available languages to translate to.
    :return: JSON object with each language key and its name in the user's language.
    """
    data = {
        "all_ALL": "ALL",
        "en_ALL": "English",
        "es_ALL": "Spanish"
    }

    return jsonify(**data)

@translate3_blueprint.route("/api/info/groups")
@cross_origin()
def info_groups():
    """
    Returns the dictionary of all available groups to translate to.
    :return:
    """
    data = {
        "ALL": "DEFAULT",
        "10-12": "Preadolescents (10-12)",
        "13-15": "Adolescents (13-15)"
    }

    return jsonify(**data)

@translate3_blueprint.route("/api/apps/<path:appurl>")
@cross_origin()
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
        "app_thumb": "http://www.golabz.eu/sites/default/files/styles/overview/public/images/app/app-image/Action%20Statistics_no_title.png",
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

@translate3_blueprint.route("/api/apps/<path:appurl>/bundles/<targetlang>", methods=["POST"])
@cross_origin()
def create_language(appurl, targetlang):
    data = {"result": "ok"}
    return jsonify(**data)

@translate3_blueprint.route("/api/apps/<path:appurl>/bundles/<targetlang>/<targetgroup>", methods=["POST"])
def create_group(appurl, targetlang, targetgroup):
    data = {"result": "ok"}
    return jsonify(**data)

@translate3_blueprint.route("/api/apps/<path:appurl>/bundles/<targetlang>/<targetgroup>/updateMessage", methods=["GET", "PUT"])
@cross_origin()
def bundle_update(appurl, targetlang, targetgroup):
    key = request.values.get("key")
    value = request.values.get("value")

    if key is None or value is None:
        data = {"result":"error"}
        return jsonify(**data)

    data = {"result": "success"}
    return jsonify(**data)