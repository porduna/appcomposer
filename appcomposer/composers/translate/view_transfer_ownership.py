from flask import render_template, request, json
from appcomposer.login import current_user
from appcomposer.appstorage.api import get_app
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import BundleManager
from appcomposer.composers.translate.db_helpers import _db_get_ownerships, _db_get_spec_apps, _db_get_lang_owner_app


# TODO: Add "security" unit-test that verifies ownership.

@translate_blueprint.route("/transfer_ownership", methods=["GET", "POST"])
def transfer_ownership():

    # No matter if we are handling a GET or POST, we require these parameters.
    appid = request.values.get("appid")

    # Retrieve the application we want to view or edit.
    app = get_app(appid)
    if app is None:
        return render_template("composers/errors.html", message="App not found"), 404

    # Make sure the logged in user owns the app.
    user = current_user()
    if app.owner != user:
        return render_template("composers/errors.html", message="Not Authorized: User does not own app"), 403

    # Get the XMLSPEC
    bm = BundleManager.create_from_existing_app(app.data)
    spec = bm.get_gadget_spec()

    # Get the language
    lang = request.values.get("lang")
    if lang is None:
        return render_template("composers/errors.html", message="Lang not specified"), 400

    # Verify that we are the owners of the language we are trying to transfer.
    owner_app = _db_get_lang_owner_app(spec, lang)
    if owner_app != app:
        return render_template("composers/errors.html", message="Not Authorized: App does not own language"), 403

    # Get the possible apps to which we can concede ownership.
    apps = _db_get_spec_apps(spec)
    apps = [a for a in apps if a != app]


    # We received a POST request. We need to transfer the ownership.
    if request.method == "POST":

        # Verify that we were passed the target app.
        targetapp = get_app(request.values.get("transfer"))
        if targetapp is None:
            return render_template("composers/errors.html", message="Target app not specified"), 400

        # Verify that the target app is of the same spec.
        targetappdata = json.loads(targetapp.data)
        targetspec = targetappdata["spec"]
        if targetspec != spec:
            return render_template("composers/errors.html", message="Target app does not have the same spec"), 400

        _db_transfer_ownership(lang, app, targetapp)

    return render_template("composers/translate/transfer_ownership.html", app=app, apps=apps, xmlspec=spec, lang=lang)