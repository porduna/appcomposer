from flask import session
import appcomposer
import appcomposer.application

from appcomposer.user import create_user, remove_user, get_user_by_login

from appcomposer import db


class TestUser:

    def __init__(self):
        self.flask_app = None

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
        user = get_user_by_login("utuser")
        if user is not None:
            remove_user(user)

    def setUp(self):
        appcomposer.app.config['DEBUG'] = True
        appcomposer.app.config['TESTING'] = True
        appcomposer.app.config['CSRF_ENABLED'] = False
        appcomposer.app.config["SECRET_KEY"] = 'secret'
        self.flask_app = appcomposer.app.test_client()
        self.flask_app.__enter__()

        # TODO: This seems to be required for this test to work.
        # We should find out why, and make sure that it is a valid reason.
        # (If it isn't, there are DB errors - apparently by doing a request the DB gets initialized).
        self.flask_app.get("/")

        # In case the test failed before, start from a clean state.
        self._cleanup()

    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

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

        assert session["logged_in"]

        rv = self.flask_app.get("/user/")
        assert rv.status_code == 200