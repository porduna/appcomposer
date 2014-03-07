from flask import session

import appcomposer
import appcomposer.application


class TestLogin:
    def login(self, username, password, redirect=True):
        return self.flask_app.post('/login', data=dict(
            login=username,
            password=password
        ), follow_redirects=redirect)

    def logout(self):
        return self.flask_app.get('/logout', follow_redirects=True)

    def setUp(self):
        appcomposer.app.config['DEBUG'] = True
        appcomposer.app.config['TESTING'] = True
        appcomposer.app.config['CSRF_ENABLED'] = False
        appcomposer.app.config["SECRET_KEY"] = 'secret'

    def tearDown(self):
        pass

    def test_login_works(self):
        self.flask_app = appcomposer.app.test_client()
        with self.flask_app:
            rv = self.login("testuser", "password")
            assert rv.status_code == 200
            assert "logged_in" in session
            assert session["login"] == "testuser"
            assert session["name"] == "Test User"

    def test_login_fails_when_wrong_pass(self):
        self.flask_app = appcomposer.app.test_client()
        with self.flask_app:
            rv = self.login("testuser", "3413124141242142342442")
            assert "logged_in" not in session
            assert "login" not in session
            assert "name" not in session

    def test_login_fails_when_wrong_user(self):
        self.flask_app = appcomposer.app.test_client()
        with self.flask_app:
            rv = self.login("testuser23414", "21412412424")
            assert "logged_in" not in session
            assert "login" not in session
            assert "name" not in session

    def test_login_redir(self):
        self.flask_app = appcomposer.app.test_client()
        with self.flask_app:
            rv = self.login("testuser", "password", False)
            assert rv.status_code == 302
            assert rv.location == "http://localhost/user/"

    def test_login_not_wrong_redir(self):
        self.flask_app = appcomposer.app.test_client()
        with self.flask_app:
            rv = self.login("testuser", "wrongpassword", False)
            assert rv.status_code != 302
            assert rv.location != "http://localhost/user/"