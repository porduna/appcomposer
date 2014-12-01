"""
To test *some* of the translate ops (such as those in ops_highlevel).
Not all tests will be here. Some ops will actually be tested through the methods in test_translate_app_creation and the
like.
"""

import json
import os
from nose.tools import raises
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name
from appcomposer.composers.translate import bundles
from appcomposer.composers.translate.bundles import BundleManager

from unittest import TestCase
from appcomposer.composers.translate.db_helpers import load_appdata_from_db
from appcomposer.composers.translate.operations import ops_highlevel
from appcomposer import models
from appcomposer import db
from appcomposer.composers.translate.operations.ops_exceptions import BundleNotFoundException


class TestTranslateOps(TestCase):
    def __init__(self, *args, **kwargs):
        TestCase.__init__(self, *args, **kwargs)
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
        self.flask_app.__enter__()

        self._cleanup()

        self.flask_app.get("/")
        rv = self.login("testuser", "password")

        # Create a test application.
        self.tapp = api.create_app("UTApp", "translate", "http://fake.spec", "{}", False)

    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

    @raises(BundleNotFoundException)
    def test_translate_load_bundle_throws_if_not_found(self):
        """
        Ensures that if the Bundle does not exist then a BundleNotFoundException is raised.
        :return:
        """
        bundle = ops_highlevel.load_bundle(self.tapp, "all_ALL", "NOT EXISTS")

    def test_translate_highlevel_load_bundle(self):
        """
        Ensures that if the bundle does exist it is retrieved successfully.
        :return:
        """

        # Create some bundles to attach.
        b = models.Bundle("all_ALL", "ALL")
        b.app = self.tapp
        m1 = models.Message("message1", "First Message")
        m2 = models.Message("message2", "Second Message")
        b.messages.append(m1)
        b.messages.append(m2)
        db.session.add(b)
        db.session.commit()

        bundle = ops_highlevel.load_bundle(self.tapp, "all_ALL", "ALL")

        self.assertIs(type(bundle), bundles.Bundle)
        self.assertEquals(2, len(bundle.get_msgs()))
        self.assertEquals(bundle.get_msg("message1"), "First Message")
        self.assertEquals(bundle.get_msg("message2"), "Second Message")

    def test_translate_highlevel_save_bundle_modifs_only(self):
        """
        Ensures that a Bundle is saved successfully to the DB when all the messages are there already.
        :return:
        """
        # Create some bundles to attach.
        b = models.Bundle("all_ALL", "ALL")
        b.app = self.tapp
        m1 = models.Message("message1", "First Message")
        m2 = models.Message("message2", "Second Message")
        b.messages.append(m1)
        b.messages.append(m2)
        db.session.add(b)
        db.session.commit()

        bundle = ops_highlevel.load_bundle(self.tapp, "all_ALL", "ALL")
        bundle.add_msg("message1", "First Message Modified")
        bundle.add_msg("message2", "Second Message Modified")

        ops_highlevel.save_bundle(self.tapp, bundle)

        # Check that it was saved properly.
        m1 = db.session.query(models.Message).filter_by(bundle=b, key="message1").first()
        self.assertEquals("First Message Modified", m1.value)
        m2 = db.session.query(models.Message).filter_by(bundle=b, key="message2").first()
        self.assertEquals("Second Message Modified", m2.value)

        msgs = db.session.query(models.Message).filter_by(bundle=b).all()
        self.assertEquals(2, len(msgs))

    def test_translate_highlevel_save_bundle_new_only(self):
        """
        Ensures that a Bundle is saved successfully to the DB when the messages are *not* there already.
        :return:
        """

        # Create the Bundle.
        b = models.Bundle("all_ALL", "ALL")
        b.app = self.tapp
        db.session.add(b)
        db.session.commit()

        bundle = bundles.Bundle("all", "ALL", "ALL")
        bundle.add_msg("message1", "First Message")
        bundle.add_msg("message2", "Second Message")

        ops_highlevel.save_bundle(self.tapp, bundle)

        # Check that it was saved properly.
        m1 = db.session.query(models.Message).filter_by(bundle=b, key="message1").first()
        self.assertEquals("First Message", m1.value)
        m2 = db.session.query(models.Message).filter_by(bundle=b, key="message2").first()
        self.assertEquals("Second Message", m2.value)

        msgs = db.session.query(models.Message).filter_by(bundle=b).all()
        self.assertEquals(2, len(msgs))

