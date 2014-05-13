import json
import urllib
import appcomposer
from appcomposer import db
from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name, get_app, update_app_data, add_var
from appcomposer.models import AppVar


class TestSecurityTranslateTransferOwnership:
    def __init__(self):
        self.flask_app = None
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

        self.login("testuser", "password")
        if self.firstApp is not None:
            app = api.get_app(self.firstApp)
            if app is not None:
                api.delete_app(app)

        self.login("testuser2", "password")
        if self.secondApp is not None:
            app = api.get_app(self.secondApp)
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
        self.firstApp = get_app_by_name("UTApp").unique_id

        rv = self.login("testuser2", "password")
        # Create the CHILDREN app
        url = "appcomposer/tests_data/relativeExample/i18n.xml"
        rv = self.flask_app.post("/composers/translate/selectlang", data={"appname": "UTApp2", "appurl": url}, follow_redirects=True)
        self.secondApp = get_app_by_name("UTApp2").unique_id

    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

    def test_nothing(self):
        pass

    def test_option_appears_on_edit(self):
        """
        Test that the transfer option does appear on the edit view.
        """
        self.login("testuser", "password")

        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp)
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.
        assert "Transfer Ownership" in data
        assert "/translate/transfer_ownership" in data

    def test_cannot_transfer_other_users_app(self):
        """
        If we try to transfer an app we do not own the request is refused with a 403 error.
        """
        self.login("testuser2", "password")

        url = u"/composers/translate/transfer_ownership?%s" % urllib.urlencode(dict(
            appid=self.firstApp,
            lang="all_ALL",
            transfer=self.secondApp
            ))
        rv = self.flask_app.post(url)
        assert rv.status_code == 403  # NOT AUTHORIZED

    def test_cannot_transfer_from_nonowner(self):
        """
        If we try to transfer an app whose language is not really an owner lang then
        the request is refused with a 403 error.
        """
        self.login("testuser2", "password")

        url = u"/composers/translate/transfer_ownership?%s" % urllib.urlencode(dict(
            appid=self.secondApp,
            lang="all_ALL",
            transfer=self.firstApp
            ))
        rv = self.flask_app.post(url)
        assert rv.status_code == 403  # NOT AUTHORIZED

    def test_cannot_transfer_into_different_spec(self):
        """
        If we try to transfer to an app with a different spec, it is refused.
        """
        # Change the spec of the second app so that we can test.
        self.login("testuser2", "password")
        secondApp = get_app(self.secondApp)
        data = json.loads(secondApp.data)
        data["spec"] = "TESTSPEC"
        secondApp.data = json.dumps(data)
        update_app_data(secondApp, data)
        specVar = db.session.query(AppVar).filter(AppVar.app == secondApp, AppVar.name == "spec").first()
        specVar.value = "TESTSPEC"
        db.session.add(specVar)
        db.session.commit()


        self.login("testuser", "password")
        url = u"/composers/translate/transfer_ownership?%s" % urllib.urlencode(dict(
            appid=self.firstApp,
            lang="all_ALL",
            transfer=self.secondApp
            ))
        rv = self.flask_app.post(url)
        print rv.status_code
        assert rv.status_code == 400 # Request denied
