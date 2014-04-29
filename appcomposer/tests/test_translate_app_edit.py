#!/usr/bin/python

import json
import os
import re
import urllib
import urllib2
import appcomposer
import appcomposer.application
from appcomposer import db

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name
from appcomposer.composers.translate.bundles import BundleManager


class TestTranslateAppEdit:
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

    def test_publish_links(self):
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        # We use regex rather than exactly predict the link itself because due to the decode workaround above
        # the ampersand in the URL gets originally replaced.
        standard_link = u"/composers/translate/publish\\?group=ALL.{1,7}appid=%s" % self.firstApp.unique_id
        assert re.search(standard_link, data) is not None

        urlstr = urllib.quote_plus(u"appcomposer/tests_data/relativeExample/i18n.xml")
        shindig_link = u"/composers/translate/serve\\?app_url=%s" % urlstr
        assert re.search(shindig_link, data) is not None

    def test_messages_expected(self):
        """
        Check that the translations present in the page seem to be the expected ones.
        """
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        assert data.count("Black") >= 2
        assert data.count("hello_world") >= 1
        assert "Hello World." in data
        assert data.count("Color") >= 2

    def test_save_works(self):
        """
        Check that Save changes the content.
        """
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        posturl = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % self.firstApp.unique_id
        postdata = {"appid": self.firstApp.unique_id,
                    "srclang": "all_ALL",
                    "targetlang": "all_ALL",
                    "srcgroup": "ALL",
                    "targetgroup": "ALL",
                    "_message_blue": "Blue",
                    "_message_hello_world": "Hello Test World",
                    "save": ""}
        rv = self.flask_app.post(posturl, data=postdata)
        assert rv.status_code == 200

        data = rv.data.decode("utf8")

        # Ensure that the change has been really saved by the post.
        assert "Hello Test World" in data
        assert "Hello World." not in data

        # Ensure that the translations that have not been specified remain as they are.
        assert data.count("Black") >= 2

    def test_save_exit_works(self):
        """
        Check that Save & Exit changes the content and redirects.
        """
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        posturl = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % self.firstApp.unique_id
        postdata = {"appid": self.firstApp.unique_id,
                    "srclang": "all_ALL",
                    "targetlang": "all_ALL",
                    "srcgroup": "ALL",
                    "targetgroup": "ALL",
                    "_message_blue": "Blue",
                    "_message_hello_world": "Hello Test World",
                    "save_exit": ""}
        rv = self.flask_app.post(posturl, data=postdata)
        assert rv.status_code == 302

        # GET again to check the changes.
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        # Ensure that the change has been really saved by the post.
        assert "Hello Test World" in data
        assert "Hello World." not in data

        # Ensure that the translations that have not been specified remain as they are.
        assert data.count("Black") >= 2

    def test_new_language_translation_creation(self):
        """
        Test that a translation for a language that does not have a translation yet is
        automatically created (for a user who owns the all_ALL language of the app).
        """
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=te_ST&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200

        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        # Ensure that the identifiers appear in the response.
        # (that is, that it appears to be translate-able)
        assert u"hello_world" in data
        assert u"black" in data

    def test_new_group_creation(self):
        """
        Test that we can create a translation for a new group, from an existing translation.
        (Translate to all_ALL_TEST).
        """
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=TEST" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200

        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        # Ensure that the identifiers appear in the response.
        # (that is, that it appears to be translate-able)
        assert u"hello_world" in data
        assert u"black" in data
        assert u"Hello World." in data

    def test_source_group_must_exist(self):
        """
        Ensure that the existence of the source group is required
        for translating anything, or otherwise a 400 error is returned.
        """
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ERR&targetgroup=TEST" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 400


    def test_source_lang_must_exist(self):
        """
        Ensure that the existence of the source language is required
        for translating anything, or otherwise a 400 error is returned.
        """
        url = u"/composers/translate/edit?appid=%s&srclang=all_ERR&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=TEST" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 400


    def test_autopropose_save_works_on_child_app(self):
        """
        Check that Save changes the content on the children app.
        """
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.secondApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        posturl = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % self.secondApp.unique_id
        postdata = {"appid": self.secondApp.unique_id,
                    "srclang": "all_ALL",
                    "targetlang": "all_ALL",
                    "srcgroup": "ALL",
                    "targetgroup": "ALL",
                    "_message_blue": "Blue",
                    "_message_hello_world": "Hello Test World",
                    "save": "",
                    "proposeToOwner": "true"}
        rv = self.flask_app.post(posturl, data=postdata)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")

        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.secondApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        # Ensure that the change has been really saved by the post.
        assert "Hello Test World" in data
        assert "Hello World." not in data
        # Ensure that the translations that have not been specified remain as they are.
        assert data.count("Black") >= 2


        # Ensure that the changes affect the PARENT app as well (because the
        # Accept All Translation Proposals Automatically switch should be turned on by default).
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        assert "Hello Test World" in data
        assert "Hello World." not in data

    def test_translate_default_autoaccept_in_selectlang(self):
        """
        Check that in the selectlang screen, the Accept Proposals Automatically switch is checked.
        (Which should be, by default).
        """
        # Ensure that "Accept all translation proposals automatically" is checked by default.
        url = u"/composers/translate/selectlang?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        assert """id="accept-proposals" checked""" in data

    def test_save_does_not_affect_parent_when_not_proposed(self):
        """
        Check that when the child app does not propose the changes to the owner,
        these changes have no effect on it.
        """
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.secondApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        posturl = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % self.secondApp.unique_id
        postdata = {"appid": self.secondApp.unique_id,
                    "srclang": "all_ALL",
                    "targetlang": "all_ALL",
                    "srcgroup": "ALL",
                    "targetgroup": "ALL",
                    "_message_blue": "Blue",
                    "_message_hello_world": "Hello Test World",
                    "save": "",
                    # proposeToOwner deliberately NOT here.
                    }
        rv = self.flask_app.post(posturl, data=postdata)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")

        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.secondApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        # Ensure that the change has been really saved by the post.
        assert "Hello Test World" in data
        assert "Hello World." not in data
        # Ensure that the translations that have not been specified remain as they are.
        assert data.count("Black") >= 2


        # Ensure that the changes DO NOT affect the PARENT app as well (accept-automatically
        # is switched on, but the child app DID NOT PROPOSE the changes).
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        assert "Hello Test World" not in data
        assert "Hello World." in data



    def test_save_propose_without_autoaccept(self):
        """
        Check that AutoAccept can be disabled, and that then the children
        app can propose the changes to the parent, and the parent sees them.
        """
        # Set Autoaccept to False
        url = u"/composers/translate/config/autoaccept/" + self.firstApp.unique_id
        rv = self.flask_app.post(url, data={"value": 0})
        assert rv.status_code == 200
        js = json.loads(rv.data)
        assert js["result"] == "success"
        assert js["value"] == False


        # Edit the child app and propose changes.
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.secondApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        posturl = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % self.secondApp.unique_id
        postdata = {"appid": self.secondApp.unique_id,
                    "srclang": "all_ALL",
                    "targetlang": "all_ALL",
                    "srcgroup": "ALL",
                    "targetgroup": "ALL",
                    "_message_blue": "Blue",
                    "_message_hello_world": "Hello Test World",
                    "save": "",
                    "proposeToOwner": "true"}
        rv = self.flask_app.post(posturl, data=postdata)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")

        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.secondApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        # Ensure that the change has been really saved by the post.
        assert "Hello Test World" in data
        assert "Hello World." not in data
        # Ensure that the translations that have not been specified remain as they are.
        assert data.count("Black") >= 2


        # Ensure that the parent now sees a proposal.
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        assert """class="badge" style>1</span>"""

