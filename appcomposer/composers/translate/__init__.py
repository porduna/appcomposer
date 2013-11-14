import os
import random

from flask import Blueprint, render_template, flash, redirect, url_for, request, json
from babel import Locale, UnknownLocaleError

from appcomposer.appstorage.api import create_app, get_app, update_app_data
from forms import UrlForm, LangselectForm


info = {
    'blueprint': 'translate',
    'url': '/composers/translate',

    'new_endpoint': 'translate.translate_index',
    'edit_endpoint': 'translate.translate_selectlang',
    'delete_endpoint': 'dummy.delete',

    'name': 'Translate Composer',
    'description': 'Translate an existing app.'
}

translate_blueprint = Blueprint(info['blueprint'], __name__)

import backend


@translate_blueprint.route('/', methods=['GET', 'POST'])
def translate_index():
    form = UrlForm(request.form)

    # If it is a POST request (steps 2 & step 3), then request.form['appvar'] will not be None
    # Otherwise we will simply load the index
    if form.validate_on_submit():
        appurl = form.get_appurl()
        flash("App loaded successfully.")
        #return redirect(request.args.get("next") or url_for("translate.translate_index"))
        return redirect(url_for("adapt.adapt_index"))

    # It was a GET request (just viewing).
    return render_template('composers/translate/index.html', form=form)


#----------------------------------------
# other pages 
#----------------------------------------


@translate_blueprint.route("/selectlang", methods=["GET", "POST"])
def translate_selectlang():
    """ Source language & target language selection."""

    # TODO: This approach has many flaws, should be changed eventually.
    # Note: The name pcode refers to the fact that the codes we deal with here are partial (do not include
    # the group).
    targetlangs_codes = ["es_ALL", "eu_ALL", "ca_ALL", "en_ALL", "de_ALL", "fr_ALL", "pt_ALL"]
    targetlangs_list = [{"pcode": code, "repr": backend.BundleManager.get_locale_english_name(
        *backend.BundleManager.get_locale_info_from_code(code))} for code in targetlangs_codes]
    groups_list = [("ALL", "ALL"), ("10-13", "Preadolescence (age 10-13)"), ("14-18", "Adolescence (age 14-18)")]

    # As of now (may change in the future) if it is a POST we are creating the app for the first time.
    # Hence, we will need to carry out a full spec retrieval.
    if request.method == "POST":
        # URL to the XML spec of the gadget.
        appurl = request.form["appurl"]

        # Get all the existing bundles.
        bm = backend.BundleManager()
        bm.load_full_spec(appurl)

        # Build JSON data
        js = bm.to_json()

        # Generate a name for the app.
        # TODO: Eventually, this name should probably be given explicitly by the user.
        appname = os.path.basename(appurl) + "_%d" % random.randint(0, 9999)

        # Create a new App from the specified XML
        app = create_app(appname, "translate", js)

        flash("App spec successfully loaded", "success")

        # Find out which locales does the app provide (for now).
        locales = bm.get_locales_list()


        # Remove from the suggested targetlangs those langs which are already present on the bundle manager,
        # because those will be added to the targetlangs by default.
        targetlangs_list_filtered = [elem for elem in targetlangs_list if elem["pcode"] not in targetlangs_codes]

        return render_template("composers/translate/selectlang.html", target_langs=targetlangs_list_filtered, groups=groups_list,
                               app=app,
                               Locale=Locale, locales=locales)

    # This was a GET, the app should exist already somehow, we will try to retrieve it.

    appid = request.args.get("appid")
    if appid is None:
        # An appid is required.
        return redirect(url_for("user.apps.index"))

    app = get_app(appid)

    flash("App successfully loaded from DB", "success")

    # TODO: Tidy up the appdata[spec] thing.
    bm = backend.BundleManager(json.loads(app.data)["spec"])
    bm.load_from_json(app.data)

    locales = bm.get_locales_list()

    # Remove from the suggested targetlangs those langs which are already present on the bundle manager,
    # because those will be added to the targetlangs by default.
    targetlangs_list_filtered = [elem for elem in targetlangs_list if elem["pcode"] not in targetlangs_codes]

    return render_template("composers/translate/selectlang.html", target_langs=targetlangs_list_filtered,
                           groups=groups_list, app=app,
                           Locale=Locale, locales=locales)



@translate_blueprint.route("/edit", methods=["GET", "POST"])
def translate_edit():
    """ Text editor for the selected language. """

    # No matter if we are handling a GET or POST, we require these parameters.
    appid = request.values["appid"]
    srclang = request.values["srclang"]
    targetlang = request.values["targetlang"]
    srcgroup = request.values["srcgroup"]
    targetgroup = request.values["targetgroup"]

    # Retrieve the application we want to view.
    # TODO: This is kinda the same for GET and POST. Consider refactoring this somehow.
    app = get_app(appid)

    bm = backend.BundleManager(json.loads(app.data)["spec"])
    bm.load_from_json(app.data)

    # Retrieve the bundles for our lang. For this, we build the code from the info we have.
    srcbundle_code = backend.BundleManager.partialcode_to_fullcode(srclang, srcgroup)
    targetbundle_code = backend.BundleManager.partialcode_to_fullcode(targetlang, targetgroup)

    srcbundle = bm.get_bundle(srcbundle_code)
    targetbundle = bm.get_bundle(targetbundle_code)

    # The target bundle doesn't exist yet. We need to create it ourselves.
    if targetbundle is None:
        lang, country = targetlang.split("_")
        targetbundle = backend.Bundle(lang, country, targetgroup)
        bm.add_bundle(targetbundle_code, targetbundle)


    # This is a GET request. We are essentially viewing-only.
    if request.method == "GET":

        return render_template("composers/translate/edit.html", app=app, srcbundle=srcbundle, targetbundle=targetbundle)

    # This is a POST request. We need to save the entries.
    else:

        # Retrieve a list of all the key-values to save. That is, the parameters which start with _message_.
        messages = [(k[len("_message_"):], v) for (k, v) in request.values.items() if k.startswith("_message_")]

        # Save all the messages we retrieved from the POST or GET params into the Bundle.
        for identifier, msg in messages:
            targetbundle.add_msg(identifier, msg)

        # Now we need to save the changes into the database.
        json_str = bm.to_json()
        update_app_data(app, json_str)

        flash("Changes have been saved", "success")
        print json_str

        # Check whether the user wants to exit or to continue editing.
        if "save_exit" in request.values:
            return redirect(url_for("user.apps.index"))

        return render_template("composers/translate/edit.html", app=app, srcbundle=srcbundle, targetbundle=targetbundle)



@translate_blueprint.route("/about")
def translate_about():
    """Information about the translator application."""
    return render_template("composers/translate/about.html")


@translate_blueprint.route('/wip', methods=['GET', 'POST'])
def translate_wip():
    """Work in progress..."""
    return render_template("composers/translate/index_test.html")        
