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
        app = api.get_app_by_name("UTApp")
        if app is not None:
            api.delete_app(app)

        app = api.get_app_by_name("UTApp2")
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
        #url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % self.firstApp.unique_id
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        print rv.data
        assert "purple" in rv.data
        assert "Propose translation" in rv.data
