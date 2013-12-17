from collections import defaultdict
import os
import random
import time
import babel

from flask import Blueprint, render_template, flash, redirect, url_for, request, json, jsonify
from babel import Locale

from appcomposer import db
from appcomposer.appstorage.api import create_app, get_app, update_app_data, set_var, add_var, remove_var
from appcomposer.models import AppVar, App
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


# This import NEEDS to be after the translate_blueprint assignment due to
# importing and cyclic dependencies issues.
import backend


@translate_blueprint.route("/merge_existing", methods=["GET", "POST"])
def translate_merge_existing():
    """
    Provides the logic for one of the merging features. This merging method
    was implemented before the "proposals" system, which is superior.
    Should probably be adapted or removed in the future.
    """
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
        appvars = AppVar.query.filter_by(name="spec", value=spec).all()
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


        # Load our own app
        bm = backend.BundleManager.create_from_existing_app(app.data)

        # Merge the srcapp into our's.
        bm.merge_json(srcapp.data)

        # Update the App's data.
        update_app_data(app, bm.to_json())

        flash("Translations merged", "success")

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
    relatedAppsIds = db.session.query(AppVar.app_id).filter_by(name="spec",
                                                               value=spec).subquery()
    ownerAppId = db.session.query(AppVar.app_id).filter(AppVar.name == "ownership",
                                                        AppVar.app_id.in_(relatedAppsIds)).first()

    if ownerAppId is None:
        return None

    ownerApp = App.query.filter_by(id=ownerAppId[0]).first()
    return ownerApp


def _db_get_children_apps(spec):
    """
    Gets from the database the Apps that are NOT the owner.
    @param spec: String to the app's original XML.
    @return: The children for the App. None if no children are found.
    """
    raise NotImplemented


#----------------------------------------
# other pages 
#----------------------------------------


def _db_get_proposals(app):
    return AppVar.query.filter_by(name="proposal", app=app).all()


@translate_blueprint.route("/get_proposal", methods=["GET"])
def get_proposal():
    """
    JSON API to get the contents of a Proposal var.
    As of now it does no checks. Lets you retrieve any proposal var as
    long as you know its IP.
    @return: JSON string containing the data.
    """
    result = {}
    proposal_id = request.values.get("proposal_id")
    if proposal_id is None:
        result["result"] = "error"
        result["message"] = "proposal_id not provided"
        return jsonify(**result)

    # Retrieve the var.
    prop = AppVar.query.filter_by(name="proposal", var_id=proposal_id).first()
    if prop is None:
        result["result"] = "error"
        result["message"] = "proposal not found"
        return jsonify(**result)

    # Parse the contents
    contents = json.loads(prop.value)
    result["result"] = "success"
    result["code"] = proposal_id
    result["proposal"] = contents

    # Add the parent's application bundle to the response, so that it can be compared
    # more easily.
    bm = backend.BundleManager.create_from_existing_app(prop.app.data)
    bundle = bm.get_bundle(contents["bundle_code"])
    if bundle:
        result["original"] = bundle.to_jsonable()["messages"]
    else:
        # If the bundle doesn't exist, the original messages dict should be empty.
        result["original"] = {}

    return jsonify(**result)


@translate_blueprint.route("/selectlang", methods=["GET", "POST"])
def translate_selectlang():
    """ Source language & target language selection."""

    # Note: The name pcode refers to the fact that the codes we deal with here are partial (do not include
    # the group).

    # We will build a list of possible languages using the babel library.
    languages = babel.core.Locale("en", "US").languages.items()
    languages.sort(key=lambda it: it[1])
    # TODO: Currently, we filter languages which contain "_" in their code so as to simplify.
    # Because we use _ throughout the composer as a separator character, trouble is caused otherwise.
    # Eventually we should consider whether we need to support special languages with _
    # on its code.
    targetlangs_codes = [lang[0] + "_ALL" for lang in languages if "_" not in lang[0]]

    targetlangs_list = [{"pcode": code, "repr": backend.BundleManager.get_locale_english_name(
        *backend.BundleManager.get_locale_info_from_code(code))} for code in targetlangs_codes]

    full_groups_list = [("ALL", "ALL"), ("10-13", "Preadolescence (age 10-13)"), ("14-18", "Adolescence (age 14-18)")]

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
        # TODO: Use a specific purpose ctor here.
        bm = backend.BundleManager()
        bm.load_full_spec(appurl)
        spec = bm.get_gadget_spec()  # For later

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
            set_var(app, "ownership", "")
        else:
            bm.merge_json(ownerApp.data)
            update_app_data(app, bm.to_json())
            flash("You are not the owner of this App, so the owner's translations have been merged", "success")

        # Find out which locales does the app provide (for now).
        translated_langs = bm.get_locales_list()

    # This was a GET, the app should exist already somehow, we will try to retrieve it.
    elif request.method == "GET":

        appid = request.args.get("appid")
        if appid is None:
            flash("appid not received", "error")

            # An appid is required.
            return redirect(url_for("user.apps.index"))

        app = get_app(appid)

        # Load a BundleManager from the app data.
        bm = backend.BundleManager.create_from_existing_app(app.data)

        spec = bm.get_gadget_spec()

        translated_langs = bm.get_locales_list()


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

    proposal_num = 0
    if is_owner:
        # Just for the count of proposals
        proposal_num = len(_db_get_proposals(app))

    # Build a dictionary. For each source lang, a list of source groups.
    src_groups_dict = defaultdict(list)
    for loc in translated_langs:
        src_groups_dict[loc["pcode"]].append(loc["group"])

    locales_codes = [tlang["pcode"] for tlang in translated_langs]

    # Remove from the suggested targetlangs those langs which are already present on the bundle manager,
    # because those will be added to the targetlangs by default.
    suggested_target_langs = [elem for elem in targetlangs_list if elem["pcode"] not in locales_codes]

    # We pass some parameters as JSON strings because they are generated dynamically
    # through JavaScript in the template.
    return render_template("composers/translate/selectlang.html",
                           app=app, # Current app object.
                           suggested_target_langs=suggested_target_langs, # Suggested (not already translated) langs
                           source_groups_json=json.dumps(src_groups_dict), # Source groups in a JSON string
                           full_groups_json=json.dumps(full_groups_list), # (To find names etc)
                           target_groups=full_groups_list, # Target groups in a JSON string
                           translated_langs=translated_langs, # Already translated langs
                           is_owner=is_owner, # Whether the loaded app has the "Owner" status
                           owner=owner, # Reference to the Owner
                           proposal_num=proposal_num)  # Number of pending translation proposals


@translate_blueprint.route("/edit", methods=["GET", "POST"])
def translate_edit():
    """ Translation editor for the selected language. """

    # No matter if we are handling a GET or POST, we require these parameters.
    appid = request.values["appid"]
    srclang = request.values["srclang"]
    targetlang = request.values["targetlang"]
    srcgroup = request.values["srcgroup"]
    targetgroup = request.values["targetgroup"]

    # Retrieve the application we want to view or edit.
    app = get_app(appid)
    if app is None:
        return render_template("composers/errors.html", message="App not found")

    bm = backend.BundleManager.create_from_existing_app(app.data)
    spec = bm.get_gadget_spec()

    # Retrieve the bundles for our lang. For this, we build the code from the info we have.
    srcbundle_code = backend.BundleManager.partialcode_to_fullcode(srclang, srcgroup)
    targetbundle_code = backend.BundleManager.partialcode_to_fullcode(targetlang, targetgroup)

    srcbundle = bm.get_bundle(srcbundle_code)
    targetbundle = bm.get_bundle(targetbundle_code)

    # The target bundle doesn't exist yet. We need to create it ourselves.
    if targetbundle is None:
        splits = targetlang.split("_")
        if len(splits) == 2:
            lang, country = splits
            targetbundle = backend.Bundle(lang, country, targetgroup)
            bm.add_bundle(targetbundle_code, targetbundle)


    # Get the owner app.
    owner_app = _db_get_owner_app(spec)
    is_owner = owner_app == app

    # This is a GET request. We are essentially viewing-only.
    if request.method == "GET":
        return render_template("composers/translate/edit.html", is_owner=is_owner, app=app, srcbundle=srcbundle,
                               targetbundle=targetbundle)

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

        propose_to_owner = request.values.get("proposeToOwner")
        if propose_to_owner is not None and owner_app != app:
            # We need to propose this Bundle to the owner.
            # Note: May be confusing: app.owner.login refers to the generic owner of the App, and not the owner
            # we are talking about in the specific Translate composer.
            proposalData = {"from": app.owner.login, "timestamp": time.time(), "bundle_code": targetbundle_code,
                            "bundle_contents": targetbundle.to_jsonable()}
            proposalJson = json.dumps(proposalData)

            # Link the proposal with the Owner app.
            add_var(owner_app, "proposal", proposalJson)

            flash("Changes have been proposed to the owner")

        # Check whether the user wants to exit or to continue editing.
        if "save_exit" in request.values:
            return redirect(url_for("user.apps.index"))

        return render_template("composers/translate/edit.html", is_owner=is_owner, app=app, srcbundle=srcbundle,
                               targetbundle=targetbundle)


@translate_blueprint.route("/about")
def translate_about():
    """Information about the translator application."""
    return render_template("composers/translate/about.html")


@translate_blueprint.route("/proposed_list", methods=["POST", "GET"])
def translate_proposed_list():
    """
    Displays the list of proposed translations.
    """

    # No matter if we are handling a GET or POST, we require these parameters.
    appid = request.values["appid"]
    app = get_app(appid)

    appdata = json.loads(app.data)

    # Ensure that only the app owner can carry out these operations.
    owner_app = _db_get_owner_app(appdata["spec"])
    if app != owner_app:
        return render_template("composers/errors.html",
                               message="Not Authorized: You don't seem to be the owner of this app")

    # Get the list of proposed translations.
    proposal_vars = _db_get_proposals(app)
    proposed_translations = []
    for prop in proposal_vars:
        propdata = json.loads(prop.value)
        propdata["id"] = str(prop.var_id)
        proposed_translations.append(propdata)

    if request.method == "POST" and request.values.get("acceptButton") is not None:
        proposal_id = request.values.get("proposals")
        if proposal_id is None:
            return render_template("composers/errors.html", message="Proposal not selected")

        merge_data = request.values.get("data")
        if merge_data is None:
            return render_template("composers/errors.html", message="Merge data was not provided")
        merge_data = json.loads(merge_data)

        # TODO: Consider creating API for this.
        # TODO: Optimize this. We already have the vars.
        proposal = AppVar.query.filter_by(app=app, var_id=proposal_id).first()
        if proposal is None:
            return render_template("composers/errors.html", message="Proposals not found")

        flash("Proposal loaded: " + proposal.value)

        data = json.loads(proposal.value)
        bundle_code = data["bundle_code"]

        proposed_bundle = backend.Bundle.from_messages(merge_data, bundle_code)

        # TODO: Improve this code.
        bm = backend.BundleManager.create_from_existing_app(app.data)
        base_bundle = bm.get_bundle(bundle_code)
        if base_bundle is None:
            # The bundle doesn't exist, so no actual merge is needed.
            bm._bundles[bundle_code] = proposed_bundle
        else:
            # Merge the proposed Bundle with our Bundle.
            merged_bundle = backend.Bundle.merge(base_bundle, proposed_bundle)
            bm._bundles[bundle_code] = merged_bundle

        update_app_data(app, bm.to_json())

        flash("Merge done.", "success")

        # Remove the proposal from the DB.
        remove_var(proposal)

        # Remove it from our current proposal list as well, so that it isn't displayed anymore.
        proposed_translations = [prop for prop in proposed_translations if prop["id"] != proposal_id]

    elif request.method == "POST" and request.values.get("denyButton") is not None:
        proposal_id = request.values.get("proposals")
        if proposal_id is None:
            return render_template("composers/errors.html", message="Proposal not selected")

        proposal = AppVar.query.filter_by(app=app, var_id=proposal_id).first()
        if proposal is None:
            return render_template("composers/errors.html", message="Proposal not found")

        remove_var(proposal)

        # Remove it from our current proposal list as well, so that it isn't displayed anymore.
        proposed_translations = [prop for prop in proposed_translations if prop["id"] != proposal_id]

    return render_template("composers/translate/proposed_list.html", app=app, proposals=proposed_translations)


