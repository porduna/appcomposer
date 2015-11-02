from flask import session

from appcomposer.tests.utils import ComposerTest
import appcomposer
import appcomposer.application


class TestLogin(ComposerTest):
    def test_login_works(self):
        rv = self.login("testuser", "password")
        assert rv.status_code == 200
        assert "logged_in" in session
        assert session["logged_in"] == True
        assert session["login"] == "testuser"
        assert session["name"] == "Test User"

    def test_login_fails_when_wrong_pass(self):
        rv = self.login("testuser", "3413124141242142342442")
        assert "logged_in" not in session
        assert "login" not in session
        assert "name" not in session

    def test_login_fails_when_wrong_user(self):
        rv = self.login("testuser23414", "21412412424")
        assert "logged_in" not in session
        assert "login" not in session
        assert "name" not in session

    def test_login_redir(self):
        rv = self.login("testuser", "password", False)
        assert rv.status_code == 302
        assert rv.location == "http://localhost/user/"

    def test_login_not_wrong_redir(self):
        rv = self.login("testuser", "wrongpassword", False)
        assert rv.status_code != 302
        assert rv.location != "http://localhost/user/"

    def test_logout(self):
        rv = self.login("testuser", "password")
        rv = self.logout()
        assert "logged_in" not in session or not session["logged_in"]
