import json
import os
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name
from appcomposer.composers.translate.bundles import BundleManager
import re


class TestAdaptCreateJsConfig:
    """
    Test the initial adapt screen.
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
        with self.flask_app:
            self.flask_app.get("/")
            app = get_app_by_name("TestApp")
            if app is not None:
                api.delete_app(app)

    def setUp(self):
        appcomposer.app.config['DEBUG'] = True
        appcomposer.app.config['TESTING'] = True
        appcomposer.app.config['CSRF_ENABLED'] = False
        appcomposer.app.config["SECRET_KEY"] = 'secret'
        self.flask_app = appcomposer.app.test_client()
        self.flask_app.get("/")
        rv = self.login("testuser", "password")

        # In case the test failed before, start from a clean state.
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def test_create_jsconfig_get(self):
        """
        Ensure that the JSCConfig creation page is what we expect.
        """
        # Ensure that the index page is what we expect. The page to choose the URL, etc.
        rv = self.flask_app.get("/composers/adapt/create/jsconfig/")
        assert rv.status_code == 200
        assert "Description" in rv.data
        assert "Name" in rv.data
        assert "Build it" in rv.data

    def test_create_jsconfig_post(self):
        """
        Ensure that we can create the JSConfig.
        """
        rv = self.flask_app.post("/composers/adapt/create/jsconfig/", data=dict(
            app_name="TestApp",
            adaptor_type="jsconfig",
            app_description=" TestDescription"
        ))

        # App created successfully.
        assert rv.status_code == 302

    def test_create_edit(self):
        """
        Ensure that we can create *and* edit.
        """
        rv = self.flask_app.post("/composers/adapt/create/jsconfig/", data=dict(
            app_name="TestApp",
            adaptor_type="jsconfig",
            app_description=" TestDescription"
        ))

        # App created successfully.
        assert rv.status_code == 302

        rv = self.flask_app.post("/composers/adapt/create/jsconfig/", data=dict(
            app_name="TestApp",
            adaptor_type="jsconfig",
            app_description=" TestDescription"
        ))

        assert rv.status_code == 200

        # Retrieve the app id. Note: This relies on the fact that the last created app appears last.
        finds = re.findall("""/adapt/edit/([a-z0-9\\-]+)""", rv.data)
        appid = finds[-1]
        assert len(appid) > 2

        # Check that we can load that app's adapt screen.
        url = "/composers/adapt/adaptors/jsconfig/edit/%s/" % appid
        rv = self.flask_app.get(url)

        print rv.data

        assert rv.status_code == 200
        assert "Adapt a guidance" in rv.data
        assert "Preview" in rv.data
