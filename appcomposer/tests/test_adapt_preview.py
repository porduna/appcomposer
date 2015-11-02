import json
import os
import appcomposer
import appcomposer.application
from appcomposer.tests.utils import LoggedInComposerTest

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name
import re


class TestAdaptPreview(LoggedInComposerTest):
    """
    Test the initial adapt screen.
    """

    def _cleanup(self):
        """
        Does cleanup tasks in case the tests failed before.
        Can be invoked *before* and *after* the tests.
        """
        self.client.get("/")
        app = get_app_by_name("TestApp")
        if app is not None:
            api.delete_app(app)

    def setUp(self):
        super(TestAdaptPreview, self).setUp()

        # Create the test app.
        rv = self.client.post("/composers/adapt/create/jsconfig/", data=dict(
            app_name="TestApp",
            adaptor_type="jsconfig",
            app_description=" TestDescription"
        ))
        finds = re.findall("""/adapt/edit/([A-Za-z0-9_\\-]+)""", rv.data)
        self.appid = finds[-1]

    def test_loggedin_preview(self):
        """
        Check that we can load that app's preview screen
        """

        url = "/composers/adapt/preview/%s/" % self.appid
        rv = self.client.get(url)

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
        rv = self.client.get(url)

        print rv.data

        assert rv.status_code == 200
        assert "Preview" in rv.data
        assert "Adapt" in rv.data
        assert "iframe" in rv.data
        assert "Adaptation URL" in rv.data
        assert "Apps" not in rv.data
