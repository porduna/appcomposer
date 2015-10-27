import json
import os
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name
import re


class TestAdaptTypeSelection:
    """
    Test the type selection screen, which has different logged-in and public modes and which shows
    a list of adaptable apps of the same spec.
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

    def test_pass(self):
        pass

    def test_base_screen_logged_in(self):
        """
        Check that the type selection screen looks somewhat right when logged in.
        """
        # TODO: Should we detect precissely non-existing app specs?
        rv = self.flask_app.get("/composers/adapt/type_selection?appurl=fake.xml")
        page = rv.data
        assert "View" in page
        assert "Duplicate" in page
        assert "Start adapting" in page
        assert "Read more" in page
        assert "Apps" in page
        assert "table" in page

    def test_base_screen_public(self):
        """
        Check that the type selection screen looks somewhat right when not logged in.
        """
        self.logout()
        rv = self.flask_app.get("/composers/adapt/type_selection?appurl=fake.xml")
        page = rv.data
        assert "View" in page
        assert "Duplicate" in page
        assert "Start adapting" in page
        assert "Read more" in page
        assert "Apps" not in page  # Logged in header should no longer be present
        assert "table" in page
