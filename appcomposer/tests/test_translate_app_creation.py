import json
import os
import appcomposer
import appcomposer.application

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
        with self.flask_app:
            self.flask_app.get("/")  # This is required to create a context. Otherwise session etc don't exist.
            app = api.get_app_by_name("UTApp")
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

    def test_translate_index(self):
        """
        Ensure that the index page is what we expect.
        """
        # Ensure that the index page is what we expect. The page to choose the URL, etc.
        rv = self.flask_app.get("/composers/translate/")
        assert rv.status_code == 200
        assert "appname" in rv.data
        assert "submit" in rv.data
        assert "appurl" in rv.data

    def test_translate_sync_creation_selectlang(self):
        """
        Ensure that we can create an app normally through a synchronous POST request to SELECTLANG.
        Note that this test relies on the accessibility of: https://dl.dropboxusercontent.com/u/6424137/i18n.xml
        """
        url = "https://dl.dropboxusercontent.com/u/6424137/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTApp", "appurl": url}, follow_redirects=True)

        # Check whether it seems to be the page we expect.
        assert rv.status_code == 200  # Page found code.
        assert rv.data.count("option") > 100  # Lots of them, because of the languages list.
        assert "submit" in rv.data
        assert "Localise" in rv.data

        # Check that we did indeed create the app properly.
        with self.flask_app:
            self.flask_app.get("/")
            app = api.get_app_by_name("UTApp")

            assert app is not None
            appdata = app.data
            assert len(appdata) > 1000

            data = json.loads(appdata)

            assert "spec" in data
            assert url == data["spec"]

            bm = BundleManager.create_from_existing_app(appdata)

            assert bm.get_gadget_spec() == url
            assert len(bm._bundles) > 3

            defaultBundle = bm.get_bundle("all_ALL_ALL")
            assert defaultBundle is not None
            assert len(defaultBundle.get_msgs()) > 6

    def test_translate_app_delete_confirmation(self):
        with self.flask_app:
            rv = self.login("testuser", "password")
            app = api.create_app("UTApp", "translate", "{'spec':'http://justatest.com'}")
            api.add_var(app, "spec", "http://justatest.com")

            # Test that a confirmation appears.
            rv = self.flask_app.get("/composers/translate/delete?appid="+app.unique_id)
            assert rv.status_code == 200
            assert "sure" in rv.data
            assert "Delete" in rv.data

    def test_translate_app_delete(self):
        with self.flask_app:
            rv = self.login("testuser", "password")
            app = api.create_app("UTApp", "translate", "{'spec':'http://justatest.com'}")
            api.add_var(app, "spec", "http://justatest.com")

            # Test that cancel works.
            rv = self.flask_app.post("/composers/translate/delete", data={"appid": app.unique_id, "cancel": "Cancel"}, follow_redirects=True)
            assert rv.status_code == 200
            assert get_app_by_name("UTApp") is not None  # Make sure it still exists.

            rv = self.flask_app.post("/composers/translate/delete", data={"appid": app.unique_id, "delete": "Delete"}, follow_redirects=True)
            assert rv.status_code == 200
            assert get_app_by_name("UTApp") is None  # Make sure it no longer exists.

    def test_translate_local_sync_creation_selectlang(self):
        """
        Ensure that we can create an app normally through a synchronous POST request to SELECTLANG.
        Note that this test relies on the accessibility of a local i18n.xml file.
        """
        url = "appcomposer/tests_data/googleExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTApp", "appurl": url}, follow_redirects=True)

        # Check whether it seems to be the page we expect.
        assert rv.status_code == 200  # Page found code.
        assert rv.data.count("option") > 100  # Lots of them, because of the languages list.
        assert "submit" in rv.data
        assert "Localise" in rv.data

        # Check that we did indeed create the app properly.
        with self.flask_app:
            self.flask_app.get("/")
            app = api.get_app_by_name("UTApp")

            assert app is not None
            appdata = app.data
            assert len(appdata) > 1000

            data = json.loads(appdata)

            assert "spec" in data
            assert url == data["spec"]

            bm = BundleManager.create_from_existing_app(appdata)

            assert bm.get_gadget_spec() == url
            assert len(bm._bundles) > 3

            defaultBundle = bm.get_bundle("all_ALL_ALL")
            assert defaultBundle is not None
            assert len(defaultBundle.get_msgs()) > 6


    def test_translate_local_sync_creation_selectlang_with_relative(self):
        """
        Ensure that we can create an app normally through a synchronous POST request to SELECTLANG.
        Note that this test relies on the accessibility of: https://dl.dropboxusercontent.com/u/6424137/i18n.xml
        """
        url = "appcomposer/tests_data/relativeExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTApp", "appurl": url}, follow_redirects=True)

        # Check whether it seems to be the page we expect.
        assert rv.status_code == 200  # Page found code.
        assert rv.data.count("option") > 100  # Lots of them, because of the languages list.
        assert "submit" in rv.data
        assert "Localise" in rv.data

        # Check that we did indeed create the app properly.
        with self.flask_app:
            self.flask_app.get("/")
            app = api.get_app_by_name("UTApp")

            assert app is not None
            appdata = app.data
            assert len(appdata) > 500

            data = json.loads(appdata)

            assert "spec" in data
            assert url == data["spec"]

            bm = BundleManager.create_from_existing_app(appdata)

            assert bm.get_gadget_spec() == url
            assert len(bm._bundles) == 2

            defaultBundle = bm.get_bundle("all_ALL_ALL")
            assert defaultBundle is not None
            assert len(defaultBundle.get_msgs()) > 6

            gerBundle = bm.get_bundle("de_ALL_ALL")
            assert gerBundle is not None
            assert len(gerBundle.get_msgs()) > 6

    def test_translate_default_autoaccept(self):
        with self.flask_app:
            rv = self.login("testuser", "password")
            app = api.create_app("UTApp", "translate", '{"spec":"http://justatest.com", "bundles":{}}')
            api.add_var(app, "spec", "http://justatest.com")

            # Test that autoaccept is True (it's the default).
            bm = BundleManager.create_from_existing_app(json.loads(app.data))
            assert bm.get_autoaccept() == True