import json
from flask import render_template, make_response, request
from appcomposer import db
from appcomposer.appstorage.api import get_app
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import Bundle, BundleManager
from appcomposer.composers.translate.db_helpers import _db_get_owner_app
from appcomposer.models import AppVar


@translate_blueprint.route('/app/<appid>/i18n/<langfile>.xml')
def app_langfile(appid, langfile):
    """
    app_langfile(appid, langfile, age)

    Provided for end-users. This is the function that provides hosting for the
    langfiles for a specified App. The langfiles are actually dynamically
    generated (the information is extracted from the Translate-specific information).

    @param appid: Appid of the App whose langfile to generate.
    @param langfile: Name of the langfile. Must follow the standard: ca_ES_ALL
    @return: Google OpenSocial compatible XML, or an HTTP error code
    if an error occurs.
    """
    app = get_app(appid)

    if app is None:
        return render_template("composers/errors.html", message="Error 404: App doesn't exist."), 404

    # The composer MUST be 'translate'
    if app.composer != "translate":
        return render_template("composers/errors.html",
                               message="Error 500: The composer for the specified App is not a Translate composer."), 500

    # Parse the appdata
    appdata = json.loads(app.data)

    bundles = appdata["bundles"]
    if langfile not in bundles:
        dbg_info = str(bundles.keys())
        return render_template("composers/errors.html",
                               message="Error 404: Could not find such language for the specified app. Available keys are: " + dbg_info), 404

    bundle = Bundle.from_jsonable(bundles[langfile])

    output_xml = bundle.to_xml()

    response = make_response(output_xml)
    response.mimetype = "application/xml"
    return response


@translate_blueprint.route('/serve')
def app_translation_serve():
    """
    Serves a translation.
    GET parameters expected:
        app_url
        lang
        target
    """
    app_xml = request.values.get("app_url")
    if app_xml is None:
        return render_template("composers/errors.html",
                               message="Error 400: Bad Request: Parameter app_url is missing."), 400

    lang = request.values.get("lang")
    if lang is None:
        return render_template("composers/errors.html",
                               message="Error 400: Bad Request: Parameter lang is missing."), 400

    target = request.values.get("target")
    if target is None:
        return render_template("composers/errors.html",
                               message="Error 400: Bad Request: Parameter target is missing."), 400

    # Retrieves the owner app from the DB.
    owner_app = _db_get_owner_app(app_xml)
    if owner_app is None:
        return render_template("composers/errors.html", message="Error 404: App not found."), 404

    # Parse the app's data.
    bm = BundleManager.create_from_existing_app(owner_app.data)

    # Build the name to request.
    bundle_name = "%s_%s" % (lang, target)
    bundle = bm.get_bundle(bundle_name)

    if bundle is None:
        dbg_info = str(bm._bundles.keys())
        return render_template("composers/errors.html",
                               message="Error 404: Could not find such language for the specified app. Available keys are: " + dbg_info), 404

    output_xml = bundle.to_xml()

    response = make_response(output_xml)
    response.mimetype = "application/xml"
    return response


@translate_blueprint.route('/serve_list')
def app_translation_serve_list():
    """
    Serves a list of translated apps, so that a cache can be updated.
    """

    # Get a list of distinct XMLs.
    specs = db.session.query(AppVar.value).filter(AppVar.name == "spec").distinct()

    output = {}

    for spec_tuple in specs:
        spec = spec_tuple[0]
        owner = _db_get_owner_app(spec)
        # TODO: Handle error.

        bm = BundleManager.create_from_existing_app(owner.data)
        bundles = bm._bundles.keys()
        etag = str(owner.modification_date)

        output[spec] = {"bundles": bundles, "etag": etag}

    response = make_response(json.dumps(output, indent=True))
    response.mimetype = "application/json"
    return response


@translate_blueprint.route('/app/<appid>/<group>/app.xml')
def app_xml_group(appid, group):
    """
    app_xml(appid, group)

    Provided for end-users. This is the function that provides hosting for the
    gadget specs for a specified App. The gadget specs are actually dynamically
    generated, as every time a request is made the original XML is obtained and
    modified.

    @param appid: Identifier of the App.
    @param group: Group that will act as a filter. If, for instance, it is set to 14-18, then only
    Bundles that belong to that group will be shown.
    @return: XML of the modified Gadget Spec with the Locales injected, or an HTTP error code
    if an error occurs.
    """
    app = get_app(appid)

    if app is None:
        return render_template("composers/errors.html", message="Error 404: App doesn't exist"), 404

    # The composer MUST be 'translate'
    if app.composer != "translate":
        return render_template("composers/errors.html",
                               message="Error 500: The composer for the specified App is not Translate"), 500

    bm = BundleManager.create_from_existing_app(app.data)
    output_xml = bm.do_render_app_xml(appid, group)

    response = make_response(output_xml)
    response.mimetype = "application/xml"
    return response


@translate_blueprint.route('/app/<appid>/app.xml')
def app_xml(appid):
    """
    app_xml(appid)

    Provided for end-users. This is the function that provides hosting for the
    gadget specs for a specified App. The gadget specs are actually dynamically
    generated, as every time a request is made the original XML is obtained and
    modified.

    @param appid: Identifier of the App.
    @return: XML of the modified Gadget Spec with the Locales injected, or an HTTP error code
    if an error occurs.
    """
    app = get_app(appid)

    if app is None:
        return render_template("composers/errors.html", message="Error 404: App doesn't exist"), 404

    # The composer MUST be 'translate'
    if app.composer != "translate":
        return render_template("composers/errors.html",
                               message="Error 500: The composer for the specified App is not Translate"), 500

    bm = BundleManager.create_from_existing_app(app.data)
    output_xml = bm.do_render_app_xml(appid)

    response = make_response(output_xml)
    response.mimetype = "application/xml"
    return response