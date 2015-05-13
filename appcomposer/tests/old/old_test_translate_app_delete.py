import json
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name, get_app
from appcomposer.composers.translate.bundles import BundleManager
from appcomposer.composers.translate.db_helpers import _db_get_app_ownerships


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
            app = api.get_app_by_name("UTApp2")
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
            app = api.create_app("UTApp", "translate", "http://justatest.com", "{'spec':'http://justatest.com'}")

            # Test that a confirmation appears.
            rv = self.flask_app.get("/composers/translate/delete?appid=" + app.unique_id)
            assert rv.status_code == 200
            assert "sure" in rv.data
            assert "Delete" in rv.data

    def test_translate_app_delete(self):
        with self.flask_app:
            rv = self.login("testuser", "password")
            app = api.create_app("UTApp", "translate", "http://justatest.com", "{'spec':'http://justatest.com'}")

            # Test that cancel works.
            rv = self.flask_app.post("/composers/translate/delete", data={"appid": app.unique_id, "cancel": "Cancel"},
                                     follow_redirects=True)
            assert rv.status_code == 200
            assert get_app_by_name("UTApp") is not None  # Make sure it still exists.

            rv = self.flask_app.post("/composers/translate/delete", data={"appid": app.unique_id, "delete": "Delete"},
                                     follow_redirects=True)
            assert rv.status_code == 200
            assert get_app_by_name("UTApp") is None  # Make sure it no longer exists.

    def test_nothing_suggested_when_simple(self):
        """
        Test that when there are no ownerships or nobody to receive the ownerships,
        the transfer selection form is not displayed.
        """
        with self.flask_app:
            rv = self.login("testuser", "password")
            app = api.create_app("UTApp", "translate", "http://justatest.com", "{'spec':'http://justatest.com'}")

            # Test that a confirmation appears.
            rv = self.flask_app.get("/composers/translate/delete?appid=" + app.unique_id)
            assert rv.status_code == 200
            assert "<select" not in rv.data
            assert "Transfer all" not in rv.data

    def test_ownership_transfer_appears(self):
        """
        Test that the transfer-all-ownerships form appears properly when it is
        supposed to (we have ownerships and can transfer them).
        """
        with self.flask_app:
            rv = self.login("testuser", "password")
            app = api.create_app("UTApp", "translate", "http://justatest.com", "{'spec':'http://justatest.com'}")
            api.add_var(app, "ownership", "all_ALL_ALL")

            app2 = api.create_app("UTApp2", "translate", "http://justatest.com", "{'spec':'http://justatest.com'}")
            app2id = app2.unique_id

            rv = self.flask_app.get("/composers/translate/delete?appid=" + app.unique_id)
            assert "<select" in rv.data
            assert "Transfer all" in rv.data
            assert app2id in rv.data

    def test_delete_with_ownership_transfer(self):
        """
        Test that we can indeed delete an application and transfer all ownerships
        at the same time.
        """
        with self.flask_app:
            rv = self.login("testuser", "password")
            app = api.create_app("UTApp", "translate", "http://justatest.com", "{'spec':'http://justatest.com'}")
            api.add_var(app, "ownership", "all_ALL_ALL")

            app2 = api.create_app("UTApp2", "translate", "http://justatest.com", "{'spec':'http://justatest.com'}")
            app2id = app2.unique_id

            # Test that cancel still works.
            rv = self.flask_app.post("/composers/translate/delete", data={"appid": app.unique_id, "cancel": "Cancel"},
                                     follow_redirects=True)
            assert rv.status_code == 200
            assert get_app_by_name("UTApp") is not None  # Make sure it still exists.


            # Test that we can delete
            rv = self.flask_app.post("/composers/translate/delete",
                                     data={"appid": app.unique_id, "delete": "Delete", "transfer": app2id},
                                     follow_redirects=True)
            assert rv.status_code == 200
            assert get_app_by_name("UTApp") is None  # Make sure it no longer exists.

            # Check that the ownership was indeed transferred to the second app.
            app2 = get_app(app2id)
            ownerships = _db_get_app_ownerships(app2)
            assert len(ownerships) == 1