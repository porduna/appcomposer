from flask import render_template, jsonify
from appcomposer.composers.translate2 import translate2_blueprint
from appcomposer.composers.translate2.translation_listing import retrieve_translations


@translate2_blueprint.route("/")
def index():
    return render_template("composers/translate2/index.html")


@translate2_blueprint.route("/translations")
def translations():
    """
    Retrieves from a local cache a subset of the app repository
    which is filtered to include only apps of interest to the
    translator (translatable apps) and extended with certain
    information (such as languages it has been translated to).

    :return: Response containing JSON with the format:
    {"translations": [{
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
    }]}
    """
    translations = {
        "translations": retrieve_translations()
    }
    return jsonify(**translations)