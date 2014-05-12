import urllib
import appcomposer
from appcomposer.appstorage import api
from appcomposer.appstorage.api import get_app_by_name


class TestTranslateTransferOwnership:
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

    def test_nothing(self):
        pass


    def test_option_appears_on_edit(self):
        """
        Test that the transfer option does appear on the edit view.
        """
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.
        assert "Transfer Ownership" in data
        assert "/translate/transfer_ownership" in data

    def test_option_doesnt_appear_if_nonowner(self):
        """
        Test that the transfer option does NOT appear on the edit view if we do not own the language.
        """
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.secondApp.unique_id)
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.
        assert "Transfer Ownership" not in data
        assert "/translate/transfer_ownership" not in data

    def test_transfer_ownership_screen_basic(self):
        """
        Test that we can load the transfer_ownership screen and that the contents are what we expect.
        """
        url = u"/composers/translate/transfer_ownership?appid=%s&lang=all_ALL" % (self.firstApp.unique_id)
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data
        print data
        #data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.
        assert "UTApp" in data
        assert "Original XML" in data
        assert "Transfer" in data
        assert "<select" in data
        assert "Test User: UTApp2" in data

    def test_transfer_ownership_post(self):
        """
        Tests that we can indeed transfer the ownership.
        """
        url = u"/composers/translate/transfer_ownership?%s" % urllib.urlencode(dict(
            appid=self.firstApp.unique_id,
            lang="all_ALL",
            transfer=self.secondApp.unique_id
            ))
        rv = self.flask_app.post(url)
        assert rv.status_code == 302

        # Verify that the ownership has indeed been transferred and can thus be transferred back by
        # secondApp.
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.secondApp.unique_id)
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.
        assert "/translate/transfer_ownership" in data

        # Verify that the original app is no longer an owner.
        url = u"/composers/translate/edit?appid=%s&srclang=all_ALL&editSelectedSourceButton=&targetlang=all_ALL&srcgroup=ALL&targetgroup=ALL" % (self.firstApp.unique_id)
        rv = self.flask_app.get(url)
        assert rv.status_code == 200
        data = rv.data.decode("utf8")  # This bypasses an apparent utf8 FlaskClient bug.
        assert "/translate/transfer_ownership" not in data

