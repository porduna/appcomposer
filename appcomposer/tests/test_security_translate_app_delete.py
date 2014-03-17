import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.models import App
from appcomposer.user import remove_user, create_user, get_user_by_login

from appcomposer import db


class TestSecurityAppDelete:
    def __init__(self):
        self.flask_app = None
        self.tapp = None
        self.user1 = None
        self.user2 = None

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
            self.flask_app.get("/")  # This is required to create a context. Otherwise session etc don't exist.
            self.user1 = get_user_by_login("utuser1")
            self.user2 = get_user_by_login("utuser2")
            remove_user(self.user1)
            remove_user(self.user2)

    def setUp(self):
        appcomposer.app.config['DEBUG'] = True
        appcomposer.app.config['TESTING'] = True
        appcomposer.app.config['CSRF_ENABLED'] = False
        appcomposer.app.config["SECRET_KEY"] = 'secret'
        self.flask_app = appcomposer.app.test_client()

        # In case the test failed before, start from a clean state.
        self._cleanup()

        with self.flask_app:
            self.flask_app.get("/")
            self.user1 = create_user("utuser1", "Test User 1", "password")
            self.user2 = create_user("utuser2", "Test User 2", "password")

    def tearDown(self):
        self._cleanup()

    def test_view_other_user_app(self):
        """
        Viewing an app that does not belong to the user SHOULD be allowed.
        """

        # Create utapp1 in utuser1
        with self.flask_app:
            rv = self.login("utuser1", "password")
            app = api.create_app("utapp1", "translate", '{"spec":"http://justatest.com", "bundles":{}}')
            api.add_var(app, "spec", "http://justatest.com")
            self.appid = app.unique_id

        # Login as utuser2 to check whether he can indeed view the app.
        # It SHOULD be view-able by anyone.
        rv = self.login("utuser2", "password")
        rv = self.flask_app.get("/composers/translate/selectlang?appid="+self.appid)
        assert rv.status_code == 200
        assert "utapp1" in rv.data

    def test_delete_other_user_app(self):
        """
        Deleting an app that does not belong to the user SHOULD NOT be allowed (and return a 401 error).
        """

        # Create utapp1 in utuser1
        with self.flask_app:
            rv = self.login("utuser1", "password")
            app = api.create_app("utapp1", "translate", '{"spec":"http://justatest.com"}')
            api.add_var(app, "spec", "http://justatest.com")
            self.appid = app.unique_id

        # Login as utuser2 to check whether he can indeed view the app.
        # It SHOULD be view-able by anyone.
        with self.flask_app:
            rv = self.login("utuser2", "password")
            rv = self.flask_app.post("/composers/translate/delete", data={"appid": app.unique_id, "delete": "Delete"}, follow_redirects=True)
            assert rv.status_code == 401  # Make sure deletion is NOT ALLOWED from a different user.
            app = db.session.query(App).filter_by(unique_id=self.appid)
            assert app is not None  # Make sure the app still exists.

    def test_not_found(self):
        """
        Trying to delete an app that doesn't exist should return a 404 error.
        """
        with self.flask_app:
            rv = self.login("utuser2", "password")
            rv = self.flask_app.post("/composers/translate/delete", data={"appid": "13414-doesnt-exist", "delete": "Delete"}, follow_redirects=True)
            assert rv.status_code == 404  # Make sure attempting to delete a non-existing app results in a 404.

        with self.flask_app:
            rv = self.login("utuser2", "password")
            rv = self.flask_app.get("/composers/translate/delete?appid=14314-not-exist", follow_redirects=True)
            assert rv.status_code == 404  # Make sure attempting to get on a non-existing app results in a 404.
