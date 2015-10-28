import json
import os
import appcomposer
import appcomposer.application
from appcomposer.tests.utils import LoggedInComposerTest

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name
import re


class TestAdaptTypeSelection(LoggedInComposerTest):
    """
    Test the type selection screen, which has different logged-in and public modes and which shows
    a list of adaptable apps of the same spec.
    """

    def _cleanup(self):
        """
        Does cleanup tasks in case the tests failed before.
        Can be invoked *before* and *after* the tests.
        """
        with self.client:
            self.client.get("/")
            app = get_app_by_name("TestApp")
            if app is not None:
                api.delete_app(app)

    def test_base_screen_logged_in(self):
        """
        Check that the type selection screen looks somewhat right when logged in.
        """
        # TODO: Should we detect precissely non-existing app specs?
        rv = self.client.get("/composers/adapt/type_selection?appurl=fake.xml")
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
        rv = self.client.get("/composers/adapt/type_selection?appurl=fake.xml")
        page = rv.data
        assert "View" in page
        assert "Duplicate" in page
        assert "Start adapting" in page
        assert "Read more" in page
        assert "Apps" not in page  # Logged in header should no longer be present
        assert "table" in page
