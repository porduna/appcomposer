from flask import session
import appcomposer
import appcomposer.application
from appcomposer.tests.utils import ComposerTest

from appcomposer.user import create_user, remove_user, get_user_by_login

from appcomposer import db


class TestUser(ComposerTest):
    def _cleanup(self):
        """
        Does cleanup tasks in case the tests failed before.
        Can be invoked *before* and *after* the tests.
        """
        user = get_user_by_login("utuser")
        if user is not None:
            remove_user(user)

    def test_user_creation_deletion(self):
        user = create_user("utuser", "Unit Test User", "password")
        assert user is not None

        user = get_user_by_login("NOTEXISTS_utuser")
        assert user is None

        user = get_user_by_login("utuser")
        assert user is not None

        user = remove_user(user)

        user = get_user_by_login("utuser")
        assert user is None

    def test_created_user_login(self):
        user = create_user("utuser", "Unit Test User", "password")
        self.login("utuser", "password")
        print session
        assert session["logged_in"]
    
        rv = self.client.get("/user/")
        assert rv.status_code == 200
