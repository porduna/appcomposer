"""
This file is meant to contain AJAX functions to be used throughout the composers.
"""

from flask import request, jsonify

from appcomposer.application import app as flask_app
from appcomposer.appstorage.api import get_app, save_app
from appcomposer.login import requires_login


@flask_app.route("/change/appname/<appid>", methods=["POST"])
@requires_login
def change_appname(appid):
    """
    Changes the appname.
    """
    result = {}

    app = get_app(appid)
    if app is None:
        result["result"] = "error"
        result["message"] = "appid not provided"
        return jsonify(**result), 400

    name = request.values.get("name")
    if name is None:
        result["result"] = "error"
        result["message"] = "new name not provided"
        return jsonify(**result), 400

    app.name = name
    save_app(app)

    result["result"] = "success"
    result["message"] = ""
    return jsonify(**result)


@flask_app.route("/change/appdescription/<appid>", methods=["POST"])
@requires_login
def change_appdescription(appid):
    """
    Changes the app description.
    """
    result = {}

    app = get_app(appid)
    if app is None:
        result["result"] = "error"
        result["message"] = "appid not provided"
        return jsonify(**result), 400

    description = request.values.get("description")
    if description is None:
        result["result"] = "error"
        result["message"] = "new description not provided"
        return jsonify(**result), 400

    app.description = description
    save_app(app)

    result["result"] = "success"
    result["message"] = ""
    return jsonify(**result)

