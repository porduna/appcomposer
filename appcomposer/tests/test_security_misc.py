import json
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.composers.translate.bundles import BundleManager

from appcomposer.application import app as flask_app


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

    def test_creation_fails_on_local_file(self):
        """
        Ensure that we cannot create a file from a local app.xml when we are
        NOT in debug mode.
        """
        flask_app.config["DEBUG"] = False
        url = "appcomposer/tests_data/googleExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTApp", "appurl": url},
                                 follow_redirects=True)

        # Check whether it seems to be the page we expect.
        assert rv.status_code != 200  # Page found code.

        # Check that we did indeed create the app properly.
        with self.flask_app:
            self.flask_app.get("/")
            app = api.get_app_by_name("UTApp")

            assert app is None
