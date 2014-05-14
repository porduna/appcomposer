import json
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name
from appcomposer.composers.translate.bundles import BundleManager


class TestTranslateAppDelete:
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