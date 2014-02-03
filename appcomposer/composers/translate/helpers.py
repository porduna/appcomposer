from flask import request, jsonify, json, render_template
from appcomposer.appstorage.api import get_app_by_name
from appcomposer.composers.translate import translate_blueprint, backend, CFG_SAME_NAME_LIMIT
from appcomposer.models import AppVar

__author__ = 'lrg'


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


def _find_unique_name_for_app(base_name):
    """
    Generates a unique (for the current user) name for the app, using a base name.
    Because two apps for the same user cannot have the same name, if the base_name that the user chose
    exists already then we append (#num) to it.

    @param base_name: Name to use as base. If it's not unique (for the user) then we will append the counter.
    @return: The generated name, guaranteed to be unique for the current user, or None, if it was not possible
    to obtain the unique name. The failure would most likely be that the limit of apps with the same name has
    been reached. This limit is specified through the CFG_SAME_NAME_LIMIT variable.
    """
    if base_name is None:
        return None

    if get_app_by_name(base_name) is None:
        return base_name
    else:
        app_name_counter = 1
        while True:
            # Just in case, enforce a limit.
            if app_name_counter > CFG_SAME_NAME_LIMIT:
                return None
            composed_app_name = "%s (%d)" % (base_name, app_name_counter)
            if get_app_by_name(composed_app_name) is not None:
                app_name_counter += 1
            else:
                # Success. We found a unique name.
                return composed_app_name


@translate_blueprint.route("/about")
def translate_about():
    """Information about the translator application."""
    return render_template("composers/translate/about.html")