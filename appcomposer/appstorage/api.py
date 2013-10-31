"""
This module contains a few appstorage-related functions which are meant to be used from
other modules.
"""

from appcomposer.login import current_user
from appcomposer.db import db_session
from appcomposer.models import App

import json


def create_app(name, composer, data):
    """
    create_app(name, data)
    @param name: Unique name to give to the application.
    @param composer: Composer identifier.
    @param data: JSON-able dictionary with the composer-specific data, or the JSON string itself.
    @return: The app that has been created.

    @note: This function can be used by any logged-on user. There are no restrictions other than
    unique (name, owner) combination.
    """

    # Get the current user, who will be the owner of our app.
    owner = current_user()

    # If the composer-specific data is already a string, we assume
    # it is JSON'ed already.
    if type(data) is not str and type(data) is not unicode:
        data = json.dumps(data)

    # Create it
    new_app = App(name, owner, composer)
    new_app.data = data

    # Insert the new app into the database
    db_session.add(new_app)
    db_session.commit()

    return new_app


def get_app(unique_id):
    """
    get_app(unique_id)
    Gets an app by its unique_id.

    @param unique_id: Unique global identifier of the app.
    @return: The app if found, None otherwise.

    @note: As of now, this function can be used by anyone. There are no
    restrictions. Not even being logged on.
    """
    app = db_session.query(App).filter_by(unique_id=unique_id).first()
    return app


def get_app_by_name(app_name):
    """
    get_app_by_name(app_name)
    Retrieves the current user's app with the specified name.

    @param app_name: Name of the application. Will be unique within the list of user's apps.
    @return: The app if found, None otherwise.

    @note: This function can only be used by logged-on users.
    """
    user = current_user()
    retrieved_app = db_session.query(App).filter_by(owner=user, name=app_name).first()
    return retrieved_app


def save_app(composed_app):
    """
    save_app(app)
    Saves the App object to the database. Useful when the object has been
    modified.
    @param app: App object
    @return: None.

    @note: This function can only be used by logged on users, and they must
    be the owners of the app being saved.
    """

    if composed_app.owner != current_user():
        raise Exception("Not Authorized")

    db_session.add(composed_app)
    db_session.commit()


def update_app_data(composed_app, data):
    """
    update_app_data(composed_app, data)
    Updates the App's composer-specific data.

    @param composed_app: Either the App object itself, or a string containing the app-id.
    @param data: Data to update the app with. Either a JSON-able dictionary, or a JSON string.

    @note: This function can only be used by logged-on users, and they must be the
    owners of the app being saved.
    """
    if type(composed_app) is str or type(composed_app) is unicode:
        composed_app = get_app(composed_app)

    if type(data) is not str and type(data) is not unicode:
        data = json.dumps(data)

    if composed_app.owner != current_user():
        raise Exception("Not Authorized")

    composed_app.data = data

    db_session.add(composed_app)
    db_session.commit()


def delete_app(composed_app):
    """
    delete_app(composed_app)
    @param composed_app: The app that we want to delete. It can either be the app object itself or an app-id.
    @return: nothing.

    @note: This function can only be used by logged-on users, and they must be the owners of
    the app being saved.
    """
    if type(composed_app) is str or type(composed_app) is unicode:
        composed_app = get_app(composed_app)

    if composed_app.owner != current_user():
        raise Exception("Not Authorized")

    db_session.delete(composed_app)
    db_session.commit()