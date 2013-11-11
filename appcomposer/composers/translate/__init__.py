import os
import random

from flask import Blueprint, render_template, flash, redirect, url_for, request
from babel import Locale

from appcomposer.appstorage.api import create_app, get_app
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
    langs_list = ["es", "eu", "ca", "en", "de", "fr", "pt"]
    groups_list = [("gen", "General"), ("10-13", "Preadolescence (age 10-13)"), ("14-18", "Adolescence (age 14-18)")]

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

        return render_template("composers/translate/selectlang.html", langs=langs_list, groups=groups_list, app=app,
                               Locale=Locale, locales=locales)

    # This was a GET, the app should exist already somehow, we will try to retrieve it.
    if "appid" in request.data:

        appid = request.data["appid"]
        app = get_app(appid)
        flash("App successfully loaded from DB", "success")

        raise NotImplementedError()

        locales = bm.get_locales_list()

        return render_template("composers/translate/selectlang.html", langs=langs_list, groups=groups_list, app=app,
                               Locale=Locale, locales=locales)

    return render_template("composers/translate/selectlang.html", langs=langs_list, groups=groups_list, Locale=Locale)


@translate_blueprint.route("/edit")
def translate_edit():
    """Text editor for the selected language."""
    return render_template("composers/translate/edit.html")


@translate_blueprint.route("/about")
def translate_about():
    """Information about the translator application."""
    return render_template("composers/translate/about.html")


@translate_blueprint.route('/wip', methods=['GET', 'POST'])
def translate_wip():
    """Work in progress..."""
    return render_template("composers/translate/index_test.html")        
