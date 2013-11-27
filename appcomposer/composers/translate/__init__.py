from collections import defaultdict
import os
import random

from flask import Blueprint, render_template, flash, redirect, url_for, request, json
from babel import Locale
from appcomposer.login import current_user

from appcomposer.appstorage.api import create_app, get_app, update_app_data, set_var, db_session
from appcomposer.models import AppVar, App, User
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


@translate_blueprint.route("/merge_existing", methods=["GET", "POST"])
def translate_merge_existing():
    appid = request.values.get("appid")
    if appid is None:
        # An appid is required.
        return redirect(url_for("user.apps.index"))
    app = get_app(appid)

    # If we are just viewing, we haven't chosen yet.
    if request.method == "GET":

        # Find out which is the XML of our app.
        data = json.loads(app.data)
        spec = data["spec"]

        # Find the Apps in the DB that match our criteria. We will need direct access to the DB, at least for now.
        appvars = db_session.query(AppVar).filter_by(name="spec", value=spec).all()
        apps_list = [var.app for var in appvars if var.app.composer == "translate"]

        return render_template('composers/translate/merge_existing.html', app=app, apps_list=apps_list)

    # It is a POST. The user has just chosen an app to merge, and we should hence carry out that merge.
    elif request.method == "POST":

        # Get the App to merge from the DB
        srcapp_id = request.values.get("srcapp")
        if srcapp_id is None:
            # The srcapp is required.
            return redirect(url_for("user.apps.index"))
        srcapp = get_app(srcapp_id)


        # Load our own App
        bm = backend.BundleManager.create_from_existing_app(app.data)

        # TODO: Better define what this load_from_json method does, and rename it to a more explicit MERGE name
        # or something similar.
        bm.load_from_json(srcapp.data)

        # Update the App's data.
        update_app_data(app, bm.to_json())

        flash("Translations merged.", "success")

        # TODO: [Offtopic]: Disable merge-to-self.

        # Redirect so that the App is reloaded with our changes applied.
        return redirect(url_for("translate.translate_selectlang", appid=appid))


@translate_blueprint.route('/', methods=['GET', 'POST'])
def translate_index():
    form = UrlForm(request.form)

    # As of now this should be a just-viewing GET request. POSTs are done
    # directly to selectlang and should actually not be received by this
    # method.
    return render_template('composers/translate/index.html', form=form)


def _db_get_owner_app(spec):
    """
    Gets from the database the App that is considered the Owner for a given spec.
    @param spec: String to the App's original XML.
    @return: The owner for the App. None if no owner is found.
    """
    relatedAppsIds = db_session.query(AppVar.app_id).filter_by(name="spec",
                                                               value=spec).subquery()
    ownerAppId = db_session.query(AppVar.app_id).filter(AppVar.name == "ownership",
                                                        AppVar.app_id.in_(relatedAppsIds)).first()

    if ownerAppId is None:
        return None

    ownerApp = db_session.query(App).filter_by(id=ownerAppId[0]).first()
    return ownerApp


def __db_get_children_apps(spec):
    """
    Gets from the database the Apps that are NOT the owner.
    @param spec: String to the app's original XML.
    @return: The children for the App. None if no children are found.
    """
    raise NotImplemented


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
    full_groups_list = [("ALL", "ALL"), ("10-13", "Preadolescence (age 10-13)"), ("14-18", "Adolescence (age 14-18)")]
    # TODO: Possible issue: What happens if the original XML contains group info? Do we take it into account?
    # TODO: Design issue, related to the above. The user should only see a limited list of source groups. However,
    # that list depends on the selected language. This means that it needs to vary dynamically depending on which
    # source language you choose.
    # TODO: For now we will solve the above by only showing the DEFAULT in the source groups list.


    # Store ownership information
    is_owner = None  # Whether the current user is the owner of the app.
    owner = None  # The owner of the app.

    # As of now (may change in the future) if it is a POST we are creating the app for the first time.
    # Hence, we will need to carry out a full spec retrieval.
    if request.method == "POST":
        # URL to the XML spec of the gadget.
        appurl = request.form.get("appurl")
        spec = appurl
        if appurl is None or len(appurl) == 0:
            flash("An application URL is required", "error")
            return redirect(url_for("translate.translate_index"))

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

        # Register our appurl as the "spec" in an app-specific variable in the DB. This will let us search later, for
        # certain advanced features.
        set_var(app, "spec", appurl)

        # Locate the owner of the App
        ownerApp = _db_get_owner_app(appurl)

        # If there isn't already an owner, declare ourselves as the owner.
        if ownerApp is None:
            flash("You are the owner of the App", "success")
            set_var(app, "ownership", "")

        flash("App spec successfully loaded", "success")

        # Find out which locales does the app provide (for now).
        locales = bm.get_locales_list()

    # This was a GET, the app should exist already somehow, we will try to retrieve it.
    elif request.method == "GET":

        appid = request.args.get("appid")
        if appid is None:
            flash("appid not received", "error")

            # An appid is required.
            return redirect(url_for("user.apps.index"))

        app = get_app(appid)

        # TODO: Tidy up the appdata[spec] thing.
        spec = json.loads(app.data)["spec"]

        flash("App successfully loaded from DB", "success")

        bm = backend.BundleManager(spec)
        bm.load_from_json(app.data)

        locales = bm.get_locales_list()


    # The following is again common for both GET (view) and POST (edit).

    # Check ownership.
    ownerApp = _db_get_owner_app(spec)
    if ownerApp == app:
        is_owner = True
    else:
        is_owner = False

    owner = ownerApp.owner

    if not is_owner and owner is None:
        flash("Error: Owner is None", "error")

    # Build a dictionary. For each source lang, a list of source groups.
    src_groups_dict = defaultdict(list)
    for loc in locales:
        src_groups_dict[loc["pcode"]].append(loc["group"])

    # Remove from the suggested targetlangs those langs which are already present on the bundle manager,
    # because those will be added to the targetlangs by default.
    targetlangs_list_filtered = [elem for elem in targetlangs_list if elem["pcode"] not in targetlangs_codes]

    return render_template("composers/translate/selectlang.html", target_langs=targetlangs_list_filtered,
                           source_groups_json=json.dumps(src_groups_dict), app=app,
                           full_groups_json=json.dumps(full_groups_list),
                           target_groups=full_groups_list,
                           Locale=Locale, locales=locales, is_owner=is_owner, owner=owner)


@translate_blueprint.route("/edit", methods=["GET", "POST"])
def translate_edit():
    """ Text editor for the selected language. """

    # No matter if we are handling a GET or POST, we require these parameters.
    appid = request.values["appid"]
    srclang = request.values["srclang"]
    targetlang = request.values["targetlang"]
    srcgroup = request.values["srcgroup"]
    targetgroup = request.values["targetgroup"]

    # Retrieve the application we want to view or edit.
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
            if len(msg) > 0:  # Avoid adding empty messages.
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

    relatedAppsIds = db_session.query(AppVar.app_id).filter_by(name="spec",
                                                               value="https://raw.github.com/ORNGatUCSF/Gadgets/master/test-opensocial-0.8.xml").subquery()

    ownerAppId = db_session.query(AppVar.app_id).filter(AppVar.name == "ownership",
                                                        AppVar.app_id.in_(relatedAppsIds)).first()

    ownerApp = db_session.query(App).filter_by(id=ownerAppId[0]).first()

    return "OWN " + str(ownerApp)

