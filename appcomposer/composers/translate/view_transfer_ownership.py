from flask import render_template, request
from appcomposer.appstorage.api import get_app
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import BundleManager


@translate_blueprint.route("/transfer_ownership", methods=["GET", "POST"])
def transfer_ownership():

    # No matter if we are handling a GET or POST, we require these parameters.
    appid = request.values.get("appid")

    # Retrieve the application we want to view or edit.
    app = get_app(appid)
    if app is None:
        return render_template("composers/errors.html", message="App not found"), 404

    # Get the XMLSPEC
    bm = BundleManager.create_from_existing_app(app.data)
    spec = bm.get_gadget_spec()

    # Get the language
    lang = request.values.get("lang")
    if lang is None:
        return render_template("composers/errors.html", message="Lang not specified"), 400

    # Get the possible apps to which we can concede ownership.


    return render_template("composers/translate/transfer_ownership.html", app=app, xmlspec=spec, lang=lang)