import json
import os
import appcomposer
import appcomposer.application

from appcomposer.tests.utils import LoggedInComposerTest
from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name
import re


class TestAdaptCreateJsConfig(LoggedInComposerTest):
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

    def test_create_jsconfig_get(self):
        """
        Ensure that the JSCConfig creation page is what we expect.
        """
        # Ensure that the index page is what we expect. The page to choose the URL, etc.
        rv = self.client.get("/composers/adapt/create/jsconfig/")
        assert rv.status_code == 200
        assert "Description" in rv.data
        assert "Name" in rv.data
        assert "Continue adapting" in rv.data

    def test_create_jsconfig_post(self):
        """
        Ensure that we can create the JSConfig.
        """
        rv = self.client.post("/composers/adapt/create/jsconfig/", data=dict(
            app_name="TestApp",
            adaptor_type="jsconfig",
            app_description=" TestDescription"
        ))

        # App created successfully.
        assert rv.status_code == 302

    def test_create_edit(self):
        """
        Ensure that we can create *and* edit.
        """
        rv = self.client.post("/composers/adapt/create/jsconfig/", data=dict(
            app_name="TestApp",
            adaptor_type="jsconfig",
            app_description=" TestDescription"
        ))

        # App created successfully.
        assert rv.status_code == 302

        rv = self.client.post("/composers/adapt/create/jsconfig/", data=dict(
            app_name="TestApp",
            adaptor_type="jsconfig",
            app_description=" TestDescription"
        ))

        assert rv.status_code == 200

        # Retrieve the app id. Note: This relies on the fact that the last created app appears last.
        finds = re.findall("""/adapt/edit/([A-Za-z0-9_\\-]+)""", rv.data)
        appid = finds[-1]
        assert len(appid) > 2

        # Check that we can load that app's adapt screen.
        url = "/composers/adapt/adaptors/jsconfig/edit/%s/" % appid
        rv = self.client.get(url)

        print rv.data

        assert rv.status_code == 200
        assert "Preview" in rv.data
