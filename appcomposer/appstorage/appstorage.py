from flask import session, render_template, render_template_string

from flask.ext.wtf import TextField, Form, PasswordField, NumberRange, DateTimeField
from flask import request, redirect, url_for, session

from appcomposer.login import current_user
from appcomposer.db import db_session
from appcomposer.application import app as flask_app
from appcomposer.models import App

import random

import json


# TODO: This whole module should be made secure, and cleaned up.


@flask_app.route('/appstorage', methods=["GET", "POST"])
def appstorage():
    return "Hello appstorage"


@flask_app.route('/appstorage/new', methods=["GET", "POST"])
def new():
    next_url = request.args.get('next', '') or request.form.get('next', '')
    name = request.args.get("name")
    if name is None:
        return "Missing parameter: name", 400
    owner = current_user()
    app = create_app(name, owner, "dummy", "{'message':'Hello world'}")
    return "Application created"


@flask_app.route('/appstorage/list', methods=["GET", "POST"])
def list():
    apps = db_session.query(App).all()

    ret = ""

    for app in apps:
        ret += "[ name: %s; id: %s ]<br>" % (app.name, app.unique_id)

    return ret


# TODO: Very important to secure this (check that the user has priviledges over the specified app).
@flask_app.route('/appstorage/<appid>', methods=["GET", "POST", "DELETE"])
def get(appid):
    app = db_session.query(App).filter_by(unique_id=appid).first()
    if app is None:
        return ("404: App doesn't exist", 404)
    if request.method == "DELETE":
        db_session.delete(app)
        db_session.commit()
    else:
        return app.to_json()


@flask_app.route('/appstorage/save', methods=["GET", "POST"])
def save():
    next_url = request.args.get('next')

    appid = request.args.get('appid', '') or request.form.get('appid', '')
    data = request.args.get('data', '') or request.form.get('data', '')

    if not data:
        return "400: Malformed Request. Data not present.", 400

    # Locate the app
    app = db_session.query(App).filter_by(unique_id=appid).first()
    if app is None:
        return "404: App doesn't exist. Can't save.", 404

    app.data = data
    app.commit()

    if next_url:
        redirect(next)
    return "App saved"


def create_app(name, owner, composer, data):
    """
    create_app(name, data)
    @param name Unique name to give to the application.
    @param owner Owner login.
    @param composer Composer identifier.
    @param data JSON-able dictionary with the composer-specific data.
    """

    # TODO: This function is very wrong. Fix it.

    data = dict(version=1, composer=composer, data=data)

    appv = App(name, owner)
    appv.data = json.dumps(data)

    # Insert the new app into the database
    db_session.add(appv)
    db_session.commit()

    return appv


def get_app(unique_id):
    """
    get_app(unique_id)
    Gets an app by its unique_id.

    @param unique_id: Unique global identifier of the app.
    @return: The app if found, None otherwise.
    """
    app = db_session.query(App).filter_by(unique_id=unique_id).first()
    return app


def get_app_by_name(app_name):
    """
    get_app_by_name(app_name)
    Retrieves the current user's app with the specified name.

    @param app_name: Name of the application. Will be unique within the list of user's apps.
    @return: The app if found, None otherwise.
    """
    user = current_user()
    appv = db_session.query(App).filter_by(owner=user, name=app_name).first()
    return appv


def save_app(composed_app):
    """
    save_app(app)
    Saves the App object to the database. Useful when the object has been
    modified.
    @param app: App object
    @return: None
    """
    db_session.add(composed_app)
    db_session.commit()