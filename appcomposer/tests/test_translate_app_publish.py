#!/usr/bin/python

import json
import re
import urllib
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name


class TestTranslateAppPublish:
    def __init__(self):
        self.flask_app = None
        self.tapp = None
        self.firstApp = None
        self.secondApp = None

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
        self.flask_app.get("/")  # This is required to create a context. Otherwise session etc don't exist.

        if self.firstApp is not None:
            app = api.get_app(self.firstApp.unique_id)
            if app is not None:
                api.delete_app(app)

        if self.secondApp is not None:
            app = api.get_app(self.secondApp.unique_id)
            if app is not None:
                api.delete_app(app)

    def setUp(self):
        appcomposer.app.config['DEBUG'] = True
        appcomposer.app.config['TESTING'] = True
        appcomposer.app.config['CSRF_ENABLED'] = False
        appcomposer.app.config["SECRET_KEY"] = 'secret'
        self.flask_app = appcomposer.app.test_client()

        self.flask_app.__enter__()

        # In case the test failed before, start from a clean state.
        self._cleanup()

        self.flask_app.get("/")
        rv = self.login("testuser", "password")

        # Create the PARENT app
        url = "appcomposer/tests_data/relativeExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTApp", "appurl": url}, follow_redirects=True)

        # Create the CHILDREN app
        url = "appcomposer/tests_data/relativeExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTApp2", "appurl": url}, follow_redirects=True)

        # We need to be in the flask client context to get app by name.
        self.flask_app.get("/")
        self.firstApp = get_app_by_name("UTApp")
        self.secondApp = get_app_by_name("UTApp2")

    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

    def test_publish_screen(self):
        """
        Check that the publish screen displays a link as it should.
        """
        url = "/composers/translate/publish?%s" % urllib.urlencode(
            dict(group="ALL", appid=self.firstApp.unique_id))
        rv = self.flask_app.get(url)
        assert rv.status_code == 200

        data = rv.data

        assert "How to publish" in data

        publish_url = "/composers/translate/app/%s/ALL/app.xml" % self.firstApp.unique_id
        print data
        assert publish_url in data

    def test_standard_publish(self):

        url = "/composers/translate/app/%s/ALL/app.xml" % self.firstApp.unique_id
        rv = self.flask_app.get(url)
        assert rv.status_code == 200

        data = rv.data

        assert "ModulePrefs" in data
        assert "EnumValue" in data
        assert "__MSG_red__" in data
        assert "/i18n/de_ALL_ALL.xml" in data
        assert "/composers/translate/app" in data

    def test_bundle_publish(self):

        url = "/composers/translate/app/%s/i18n/de_ALL_ALL.xml" % self.firstApp.unique_id
        rv = self.flask_app.get(url)
        assert rv.status_code == 200

        data = rv.data

        assert "Blau" in data
        assert "Hallo Welt." in data
        assert "Schwarz" in data
        assert "Farbe" in data
        assert "<messagebundle>" in data

    def test_shindig_serve(self):

        app_url = "appcomposer/tests_data/relativeExample/i18n.xml"
        url = "/composers/translate/serve?%s" % urllib.urlencode({"app_url": app_url,
                                                                  "lang": "all_ALL", "target": "ALL"})
        rv = self.flask_app.get(url)
        assert rv.status_code == 200

        data = rv.data

        assert "Hello World." in data
        assert "Black" in data
        assert "Color" in data
        assert "<messagebundle>" in data


    def test_shindig_serve_list(self):
        """
        Tests that the SERVE_LIST API made available to shindig works
        as expected. The serve_list API is meant to provide a list of
        apps and eTags.
        """
        url = "/composers/translate/serve_list"
        rv = self.flask_app.get(url)

        assert rv.status_code == 200
        data = rv.data

        assert "all_ALL_ALL" in data
        assert "relativeExample/i18n.xml" in data
        assert "etag" in data
        



