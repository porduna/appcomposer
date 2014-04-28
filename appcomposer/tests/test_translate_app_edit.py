 #!/usr/bin/python
 # -*- coding: utf-8 -*-

import json
import os
import appcomposer
import appcomposer.application
from appcomposer import db

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name
from appcomposer.composers.translate.bundles import BundleManager


class TestTranslateAppCreation:
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

    def test_edit_app_not_found(self):
        rv = self.flask_app.get("/composers/translate/edit?appid=1341234124314&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL")
        assert rv.status_code == 404
        assert "not found" in rv.data

    def test_just_edit_default(self):
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200

        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        assert u"purple" in data

        assert u"View Published Translation" in data
        assert u"View Shindig Translation" in data

    def test_simple_ownership(self):
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200

        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        # Ensure that we (testuser), as owner, we have no propose translation button.
        assert u"Propose translation" not in data

        assert u"You are the owner" in data

    def test_simple_non_ownership(self):
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.secondApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200

        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        # Ensure that we (testuser), as as non-owners of the second app, we can propose translations.
        assert u"Propose translation" in data

        # Ensure that the non-owner explanation appears.
        assert u"You are not the owner" in data

