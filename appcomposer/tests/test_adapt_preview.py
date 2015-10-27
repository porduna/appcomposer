import json
import os
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name
import re


class TestAdaptPreview:
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

        # In case the test failed before, start from a clean state.
        self._cleanup()

        rv = self.login("testuser", "password")

        # Create the test app.
        rv = self.flask_app.post("/composers/adapt/create/jsconfig/", data=dict(
            app_name="TestApp",
            adaptor_type="jsconfig",
            app_description=" TestDescription"
        ))
        finds = re.findall("""/adapt/edit/([A-Za-z0-9_\\-]+)""", rv.data)
        self.appid = finds[-1]


    def tearDown(self):
        self._cleanup()

    def test_pass(self):
        pass

    def test_loggedin_preview(self):
        """
        Check that we can load that app's preview screen
        """

        url = "/composers/adapt/preview/%s/" % self.appid
        rv = self.flask_app.get(url)

        print rv.data

        assert rv.status_code == 200
        assert "Preview" in rv.data
        assert "Adapt" in rv.data
        assert "iframe" in rv.data
        assert "Adaptation URL" in rv.data
        assert "Apps" in rv.data

    def test_public_preview(self):
        """
        Check that we can load that app's preview screen even when logged out
        (and that we see it differently)
        """

        self.logout()

        url = "/composers/adapt/preview/%s/" % self.appid
        print "URL: " + url
        rv = self.flask_app.get(url)

        print rv.data

        assert rv.status_code == 200
        assert "Preview" in rv.data
        assert "Adapt" in rv.data
        assert "iframe" in rv.data
        assert "Adaptation URL" in rv.data
        assert "Apps" not in rv.data
