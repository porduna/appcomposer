#!/usr/bin/python

import datetime
import json
import appcomposer
from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name

from appcomposer.composers.translate import mongodb_pusher as pusher
from appcomposer.composers.translate.bundles import Bundle
from appcomposer.composers.translate.updates_handling import on_leading_bundle_updated

import time


class TestMongoDBPusher:
    def __init__(self):
        self.flask_app = None

    def login(self, username, password):
        return self.flask_app.post('/login', data=dict(
            login=username,
            password=password
        ), follow_redirects=True)

    def _cleanup(self):
        """
        Does cleanup tasks in case the tests failed before.
        Can be invoked *before* and *after* the tests,
        and it is meant to be idempotent.
        """
        pusher.mongo_bundles.remove({"spec": "appcomposer/tests_data/relativeExample/i18n.xml"})
        pusher.mongo_bundles.remove({"bundle": "test_TEST_TEST"})
        pusher.mongo_bundles.remove({"bundle": "test_CELERYTEST_ALL"})

        with self.flask_app:
            self.flask_app.get("/")  # This is required to create a context. Otherwise session etc don't exist.
            app = api.get_app_by_name("UTApp")
            if app is not None:
                api.delete_app(app)
            app = api.get_app_by_name("UTAppChild")
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

    def tearDown(self):
        self._cleanup()

    def test_connection(self):
        assert pusher.mongo_client.alive()

    def test_mongodb_pusher(self):
        t = datetime.datetime.utcnow()
        pusher.push.apply(args=["app.xml", "test_TEST_TEST", "test data", t])

        testbundle = pusher.mongo_bundles.find_one({"bundle": "test_TEST_TEST", "spec": "app.xml"})
        assert testbundle is not None
        assert testbundle["bundle"] == "test_TEST_TEST"
        assert testbundle["spec"] == "app.xml"

        print testbundle["time"]
        assert abs((t - testbundle["time"]).seconds < 1)
        assert testbundle["data"] == "test data"

    def test_celery_mongodb_pusher(self):
        """
        Tests that the pusher works, including celery. RabbitMQ and the Celery worker must be running before
        running this test.
        """
        # Create a test bundle
        b = Bundle("test", "CELERYTEST", "ALL")
        async_result = on_leading_bundle_updated("test_app.xml", b)

        # Wait for the async task to finish. This is normally not done.
        async_result.wait()

        testbundle = pusher.mongo_bundles.find_one({"bundle": "test_CELERYTEST_ALL", "spec": "test_app.xml"})
        assert testbundle is not None
        assert testbundle["bundle"] == "test_CELERYTEST_ALL"
        assert testbundle["spec"] == "test_app.xml"

    def test_mongodb_pusher_at_app_creation(self):
        """
        Ensures that when a new (owner) app is created, all its pre-existing bundles are pushed into the MongoDB.
        """
        # Create the test app
        self.login("testuser", "password")
        url = "appcomposer/tests_data/relativeExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTApp", "appurl": url},
                                 follow_redirects=True)
        assert rv.status_code == 200  # Page found code.

        # Ensure that after a short while we have all the bundles in the MongoDB.
        time.sleep(1)

        bundles = pusher.mongo_bundles.find({"spec": url})
        bundles = {b["bundle"]: b for b in bundles}

        print bundles

        assert len(bundles) == 2

        data = bundles["all_ALL_ALL"]["data"]
        data = json.loads(data)
        assert data["hello_world"] == "Hello World."

        data = bundles["de_ALL_ALL"]["data"]
        data = json.loads(data)
        assert data["hello_world"] == "Hallo Welt."

    def test_mongodb_pusher_at_app_edit(self):
        """
        Ensures that when an existing app is edited, the changes are reflected into the MongoDB.
        """
        # Create the test app
        self.login("testuser", "password")
        appurl = "appcomposer/tests_data/relativeExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTApp", "appurl": appurl},
                                 follow_redirects=True)
        assert rv.status_code == 200  # Page found code.
        with self.flask_app:
            self.flask_app.get("/")
            testAppID = get_app_by_name("UTApp").unique_id

        # Edit the test app
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (
            testAppID)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        posturl = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % testAppID
        postdata = {"appid": testAppID,
                    "srclang": "all_ALL",
                    "targetlang": "all_ALL",
                    "srcgroup": "ALL",
                    "targetgroup": "ALL",
                    "_message_blue": "Blue",
                    "_message_hello_world": "Hello Test World",
                    "save_exit": ""}
        rv = self.flask_app.post(posturl, data=postdata)
        assert rv.status_code == 302

        # Ensure that after a short while we have all the bundles in the MongoDB and the changes have been applied.
        time.sleep(1)

        bundles = pusher.mongo_bundles.find({"spec": appurl})
        bundles = {b["bundle"]: b for b in bundles}
        print bundles
        assert len(bundles) == 2

        data = bundles["all_ALL_ALL"]["data"]
        data = json.loads(data)

        # Test that the changes have been applied.
        assert data["hello_world"] == "Hello Test World"

    def test_mongodb_pusher_at_app_edit_non_owner_propose_disabled(self):
        """
        Ensures that when an existing app is edited, if the language is not the owner, then the changes
        are NOT reflected into the MongoDB. (Proposal is not done).
        """
        # Create the FIRST (owner) test app
        self.login("testuser", "password")
        appurl = "appcomposer/tests_data/relativeExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTApp", "appurl": appurl},
                                 follow_redirects=True)
        assert rv.status_code == 200  # Page found code.

        # Create the SECOND (non-owner) test app
        self.login("testuser", "password")
        appurl = "appcomposer/tests_data/relativeExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTAppChild", "appurl": appurl},
                                 follow_redirects=True)
        assert rv.status_code == 200  # Page found code.
        with self.flask_app:
            self.flask_app.get("/")
            testAppID = get_app_by_name("UTAppChild").unique_id

        # Edit the test app
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (
            testAppID)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        posturl = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % testAppID
        postdata = {"appid": testAppID,
                    "srclang": "all_ALL",
                    "targetlang": "all_ALL",
                    "srcgroup": "ALL",
                    "targetgroup": "ALL",
                    "_message_blue": "Blue",
                    "_message_hello_world": "Hello Test World",
                    "save_exit": "",
                    #"proposeToOwner": ""
                    }
        rv = self.flask_app.post(posturl, data=postdata)
        assert rv.status_code == 302

        # Ensure that after a short while we have all the bundles in the MongoDB and the changes have been applied.
        time.sleep(1)

        bundles = pusher.mongo_bundles.find({"spec": appurl})
        bundles = {b["bundle"]: b for b in bundles}
        print bundles
        assert len(bundles) == 2

        data = bundles["all_ALL_ALL"]["data"]
        data = json.loads(data)

        # Test that the changes have NOT been applied. That is, that MongoDB still contains the translation
        # of the parent, which does not have the children's modifications.
        assert data["hello_world"] == "Hello World."

    def test_mongodb_pusher_at_app_edit_non_owner_propose_enabled(self):
        """
        Ensures that when an existing app is edited, if the language is not the owner, but autoproposals are enabled
        (by default) and a proposal is done, then the changes are applied and reported to the MongoDB.
        """
        # Create the FIRST (owner) test app
        self.login("testuser", "password")
        appurl = "appcomposer/tests_data/relativeExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTApp", "appurl": appurl},
                                 follow_redirects=True)
        assert rv.status_code == 200  # Page found code.

        # Create the SECOND (non-owner) test app
        self.login("testuser", "password")
        appurl = "appcomposer/tests_data/relativeExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTAppChild", "appurl": appurl},
                                 follow_redirects=True)
        assert rv.status_code == 200  # Page found code.
        with self.flask_app:
            self.flask_app.get("/")
            testAppID = get_app_by_name("UTAppChild").unique_id

        # Edit the test app
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (
            testAppID)
        print "URL: " + url
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.

        posturl = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % testAppID
        postdata = {"appid": testAppID,
                    "srclang": "all_ALL",
                    "targetlang": "all_ALL",
                    "srcgroup": "ALL",
                    "targetgroup": "ALL",
                    "_message_blue": "Blue",
                    "_message_hello_world": "Hello Test World",
                    "save_exit": "",
                    "proposeToOwner": ""
                    }
        rv = self.flask_app.post(posturl, data=postdata)
        assert rv.status_code == 302

        # Ensure that after a short while we have all the bundles in the MongoDB and the changes have been applied.
        time.sleep(1)

        bundles = pusher.mongo_bundles.find({"spec": appurl})
        bundles = {b["bundle"]: b for b in bundles}
        print bundles
        assert len(bundles) == 2

        data = bundles["all_ALL_ALL"]["data"]
        data = json.loads(data)

        # Test that the changes have been applied. This is expected, because though the modified lang was
        # the child, a proposal was sent and proposals are by default set to autoaccept.
        assert data["hello_world"] == "Hello Test World"

    def test_nothing(self):
        pass

