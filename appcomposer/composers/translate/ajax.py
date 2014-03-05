from flask import request, jsonify, json
import time
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import BundleManager
from appcomposer.composers.translate.db_helpers import _db_get_ownerships
from appcomposer.models import AppVar
from appcomposer.composers.translate.tasks import extract_opensocial_app


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
    bm = BundleManager.create_from_existing_app(prop.app.data)
    bundle = bm.get_bundle(contents["bundle_code"])
    if bundle:
        result["original"] = bundle.to_jsonable()["messages"]
    else:
        # If the bundle doesn't exist, the original messages dict should be empty.
        result["original"] = {}

    return jsonify(**result)


@translate_blueprint.route("/get_ownership_list", methods=["GET"])
def get_ownership_list():
    """
    JSON API to get a list of every translated language for the specified
    APP, and the Username and UserID of its owner.
    @return: JSON string containing the data.
    """
    result = {}
    xmlspec = request.values.get("xmlspec")
    if xmlspec is None:
        result["result"] = "error"
        result["message"] = "xmlspec not provided"
        return jsonify(**result)

    # Retrieve every single "owned" App for that xmlspec.
    ownerships = _db_get_ownerships(xmlspec)

    # Parse the contents
    result["result"] = "success"
    result["owners"] = {}

    for ownership in ownerships:
        language = ownership.value
        owner = ownership.app.owner
        result["owners"][language] = {"owner_id": owner.id, "owner_login": owner.login, "owner_app": ownership.app.id}

    return jsonify(**result)


@translate_blueprint.route("/test")
def test():
    ar = extract_opensocial_app.delay("http://www.google.com")
    time.sleep(1)
    if ar.result is not None:
        print "RESULT: " + ar.result
    return "HELLO"