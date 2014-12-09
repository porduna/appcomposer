import urllib
from flask import json
from werkzeug.utils import escape
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api, add_var
from appcomposer.appstorage.api import get_app
from appcomposer.composers.translate.db_helpers import _db_declare_ownership, _db_get_lang_owner_app, _db_get_ownerships, \
    _db_get_proposals
from appcomposer.composers.translate.operations.ops_highlevel import find_unique_name_for_app
from appcomposer.login import current_user


class TestAjax:
    """
    Test the AJAX functions for all composers (not the composer-specific ones)
    """
    def __init__(self):
        self.flask_app = None
        self.tapp = None

    def login(self, username, password):
        return self.flask_app.post('/login', data=dict(
            login=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.flask_app.get('/logout', follow_redirects=True)

    def _cleanup(self):
        """
        Does cleanup tasks in case the tests failed before.
        Can be invoked *before* and *after* the tests.
        """
        app = api.get_app_by_name("UTApp")
        if app is not None:
            api.delete_app(app)

        app = api.get_app_by_name("UTApp2")
        if app is not None:
            api.delete_app(app)

        app = api.get_app_by_name("UTApp (1)")
        if app is not None:
            api.delete_app(app)

        app = api.get_app_by_name("RenamedApp")
        if app is not None:
            api.delete_app(app)

    def setUp(self):
        appcomposer.app.config['DEBUG'] = True
        appcomposer.app.config['TESTING'] = True
        appcomposer.app.config['CSRF_ENABLED'] = False
        appcomposer.app.config["SECRET_KEY"] = 'secret'
        self.flask_app = appcomposer.app.test_client()
        self.flask_app.__enter__()

        rv = self.login("testuser", "password")

        # In case the test failed before, start from a clean state.
        self._cleanup()

        # Create an App for the tests.
        self.tapp = api.create_app("UTApp", "translate", "http://justatest.com", '{"spec":"http://justatest.com"}')

    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

    def test_pass(self):
        pass

    def test_change_name(self):
        """
        Test that changing the name of the app works.
        """

        post_url = u"/change/appname/" + self.tapp.unique_id
        rv = self.flask_app.post(post_url, data={"name": "RenamedApp"})

        assert rv.status_code == 200
        js = json.loads(rv.data)
        assert js["result"] == "success"

        # Ensure that the App Description changed.
        tapp = api.get_app(self.tapp.unique_id)
        assert tapp.name == "RenamedApp"

    def test_change_description(self):
        """
        Test that changing the description of the app works.
        """

        post_url = u"/change/appdescription/" + self.tapp.unique_id
        rv = self.flask_app.post(post_url, data={"description": "A new App description"})

        assert rv.status_code == 200
        js = json.loads(rv.data)
        assert js["result"] == "success"

        # Ensure that the App Name changed.
        tapp = api.get_app(self.tapp.unique_id)
        assert tapp.description == "A new App description"

