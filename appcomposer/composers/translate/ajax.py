from flask import request, jsonify, json, Response
import requests
from appcomposer.appstorage.api import get_app, update_app_data
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import BundleManager, AUTOACCEPT_DEFAULT
from appcomposer.composers.translate.db_helpers import _db_get_ownerships
from appcomposer.csrf import verify_ajax_csrf
from appcomposer.models import AppVar
from appcomposer.login import requires_login

@translate_blueprint.route("/appslist_proxy", methods=["GET"])
@requires_login
def appslist_proxy():
    """
    Retrieves a list of the App repository through the external GoLabz API.
    Returns the list in JSON.
    """
    list = requests.get("http://www.golabz.eu/rest/apps/retrieve.json")
    if list.status_code != 200:
        result = {}
        result["result"] = "error"
        result["message"] = "Could not retrieve apps data from the repository"
        return jsonify(**result)

    ret = list.text
    return Response(ret, mimetype="application/json")


@translate_blueprint.route("/config/autoaccept/<appid>", methods=["GET", "POST"])
@requires_login
def autoaccept(appid):
    """
    JSON API to GET or POST whether to auto-accept all proposals for an app or not.
    The POST request takes a "value" POST parameter.
    Both return a JSON: { result: "success", value: "<0|1>" } when successful.
    The 0 and 1 numbers are always strings.
    """
    result = {}

    app = get_app(appid)
    if app is None:
        result["result"] = "error"
        result["message"] = "appid not provided"
        return jsonify(**result)

    data = json.loads(app.data)

    if request.method == "GET":
        result["value"] = data.get("autoaccept", AUTOACCEPT_DEFAULT)
        result["result"] = "success"
        return jsonify(**result)

    if request.method == "POST":

        if not verify_ajax_csrf(request):
            result["result"] = "error"
            result["message"] = "CSRF token not valid"
            return jsonify(**result)

        value = request.values.get("value")
        if value is None:
            result["result"] = "error"
            result["message"] = "value not provided"
            return jsonify(**result)

        if value == "0":
            data["autoaccept"] = False
        elif value == "1":
            data["autoaccept"] = True
        else:
            result["result"] = "error"
            result["message"] = "Value not recognized. Should be 0 or 1."
            return jsonify(**result)

        update_app_data(app, json.dumps(data))

        result["result"] = "success"
        result["value"] = value == "1"
        return jsonify(**result)


@translate_blueprint.route("/get_proposal", methods=["GET"])
@requires_login
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
@requires_login
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
