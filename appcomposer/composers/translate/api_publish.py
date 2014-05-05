import json
import urllib2
import traceback
import xml.dom.minidom as minidom
from flask import render_template, make_response, request
from appcomposer import db
from appcomposer.appstorage.api import get_app
from appcomposer.utils import get_original_url
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import Bundle, BundleManager
from appcomposer.composers.translate.db_helpers import _db_get_lang_owner_app, _db_get_ownerships
from appcomposer.models import AppVar


@translate_blueprint.route('/serve')
def app_translation_serve():
    """
    Serves a translation through the API that SHINDIG expects.
    GET parameters expected:
        app_url
        lang
        target
    """
    app_xml = request.values.get("app_url")
    if app_xml is None:
        return render_template("composers/errors.html",
                               message="Error 400: Bad Request: Parameter app_url is missing."), 400
    try:
        # XXX FIXME
        # TODO: this makes this method to call twice the app_xml. We shouldn't need
        # that. We should have the contents here downloaded for later.
        if app_xml.startswith(('http://','https://')):
            print app_xml
            xmldoc = minidom.parseString(urllib2.urlopen(app_xml).read())
            app_xml = get_original_url(xmldoc, app_xml)
            print "New app xml:", app_xml
    except:
        traceback.print_exc()
        pass


    lang = request.values.get("lang")
    if lang is None:
        return render_template("composers/errors.html",
                               message="Error 400: Bad Request: Parameter lang is missing."), 400
    if len(lang) == 2:
        lang = '%s_ALL' % lang

    target = request.values.get("target")
    if target is None:
        return render_template("composers/errors.html",
                               message="Error 400: Bad Request: Parameter target is missing."), 400

    owner_app = _db_get_lang_owner_app(app_xml, lang)

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
    Aims to be SHINDIG-compatible, though it doesn't implement this feature yet.

    This is the new version (for the new ownership system). It is somewhat inefficient
    and the current etag scheme doesn't make much sense anymore.
    """

    # Get a list of distinct XMLs.
    specs = db.session.query(AppVar.value).filter(AppVar.name == "spec").distinct()

    output = {}

    for spec_tuple in specs:
        spec = spec_tuple[0]

        # For each spec we get the ownerships.
        ownerships = _db_get_ownerships(spec)

        bundles = []

        for ownership in ownerships:
            lang = ownership.value
            bm = BundleManager.create_from_existing_app(ownership.app.data)
            keys = [key for key in bm._bundles.keys() if BundleManager.fullcode_to_partialcode(key) == lang]

            etag = str(ownership.app.modification_date)
            bundles.append({"keys": keys, "etag": etag})

        output[spec] = {"bundles": bundles}

    response = make_response(json.dumps(output, indent=True))
    response.mimetype = "application/json"
    return response


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


@translate_blueprint.route('/app/<appid>/<group>/app.xml')
def app_xml(appid, group):
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
