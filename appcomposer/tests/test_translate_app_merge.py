#!/usr/bin/python

import json
import re
import urllib
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name


class TestTranslateAppMerge:
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

        # *** Force the creation of a proposal into the firstApp (the parent app).
        # Set Autoaccept to False
        url = u"/composers/translate/config/autoaccept/" + self.firstApp.unique_id
        rv = self.flask_app.post(url, data={"value": 0})
        assert rv.status_code == 200
        # Edit the child app and propose changes.
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.secondApp.unique_id)
        rv = self.flask_app.get(url)
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
        # Access the parent's selectlang to see the proposal button.
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.
        assert """class="badge" style>1</span>"""



    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

    def test_proposal_screen_basic(self):
        """
        Check that we can access the proposal screen and see a proposal.
        """
        # Access the merge screen itself.
        url = u"/composers/translate/proposed_list?appid=%s" % self.firstApp.unique_id
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")

        # Ensure that the translation appears on the list.
        assert "testuser's all_ALL_ALL" in data

        # Ensure there is a single translation.
        assert "translation (1)" in data

    def test_ajax_get_proposal(self):
        # Access the merge screen itself.
        url = u"/composers/translate/proposed_list?appid=%s" % self.firstApp.unique_id
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")

        # Extract the proposal ID.
        matches = re.findall("""option value="([0-9]+)">""", data)
        proposal_id = int(matches[0])


        # Get the proposal info through AJAX.
        url = u"/composers/translate/get_proposal?proposal_id=%d" % proposal_id
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data

        # Check that the proposal description is the valid JSON we expect,
        # and that the contents of the proposal are what we expect.
        proposal_data = json.loads(data)
        proposal = proposal_data["proposal"]
        assert proposal["from"] == "testuser"
        assert proposal_data["result"] == "success"

        bundle = proposal["bundle_contents"]
        assert bundle["lang"] == "all"
        assert bundle["country"] == "ALL"
        assert bundle["group"] == "ALL"

        original = proposal_data["original"]
        assert "hello_world" in original
        assert original["hello_world"] == "Hello World."

        messages = bundle["messages"]
        assert "purple" in messages
        assert "blue" in messages
        assert "hello_world" in messages
        assert messages["hello_world"] == "Hello Test World"

    def test_ajax_accept_proposal(self):

        # Extract the proposal ID.
        url = u"/composers/translate/proposed_list?appid=%s" % self.firstApp.unique_id
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")
        matches = re.findall("""option value="([0-9]+)">""", data)
        proposal_id = int(matches[0])

        # Build the POST's data.
        mergedata = {"blue": "Blue", "hello_world": "Hello Yet Again Testing", "color": "Color Test"}
        postdata = {"data": json.dumps(mergedata),
                    "appid": self.firstApp.unique_id,
                    "proposals": proposal_id,
                    "acceptButton": ""}

        rv = self.flask_app.post(url, data=postdata)
        assert rv.status_code == 200


        # Verify that the suggested changes were applied.
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.
        # Ensure that the change has been really saved by the post.

        print "DATA IS %r" % data

        assert "Hello Yet Again Testing" in data
        assert "Color Test" in data
        # Ensure that the translations that have not been specified remain as they are.
        assert data.count("Black") >= 2


    def test_ajax_accept_proposal_removes_it(self):
        # Extract the proposal ID.
        url = u"/composers/translate/proposed_list?appid=%s" % self.firstApp.unique_id
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")
        matches = re.findall("""option value="([0-9]+)">""", data)
        proposal_id = int(matches[0])

        # Build the POST's data.
        mergedata = {"blue": "Blue", "hello_world": "Hello Yet Again Testing", "color": "Color Test"}
        postdata = {"data": json.dumps(mergedata),
                    "appid": self.firstApp.unique_id,
                    "proposals": proposal_id,
                    "acceptButton": ""}

        rv = self.flask_app.post(url, data=postdata)
        assert rv.status_code == 200

        # Access the parent's selectlang to see the proposal button.
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.
        assert """class="badge" style>0</span>"""


    def test_ajax_deny_proposal_removes_it(self):
        """
        To check that denying a proposal removes it without
        applying the changes.
        """
        # Extract the proposal ID.
        url = u"/composers/translate/proposed_list?appid=%s" % self.firstApp.unique_id
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")
        matches = re.findall("""option value="([0-9]+)">""", data)
        proposal_id = int(matches[0])

        # Build the POST's data.
        mergedata = {"blue": "Blue", "hello_world": "Hello Yet Again Testing", "color": "Color Test"}
        postdata = {"data": json.dumps(mergedata),
                    "appid": self.firstApp.unique_id,
                    "proposals": proposal_id,
                    "denyButton": ""}

        rv = self.flask_app.post(url, data=postdata)
        assert rv.status_code == 200

        # Access the parent's selectlang to see the proposal button.
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.
        assert """class="badge" style>0</span>"""  # Check that it was removed.

        # Verify that the suggested changes were NOT applied.
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.
        # Ensure that the change has NOT been applied.
        assert "Hello Yet Again Testing" not in data
        assert "Color Test" not in data
        assert "Hello World." in data
        # Ensure that the translations that have not been specified remain as they are.
        assert data.count("Black") >= 2



