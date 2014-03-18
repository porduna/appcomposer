import urllib
from flask import json
from werkzeug.utils import escape
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api, add_var
from appcomposer.appstorage.api import get_app
from appcomposer.composers.translate.db_helpers import _db_declare_ownership, _db_get_lang_owner_app, _db_get_ownerships, _find_unique_name_for_app, _db_get_proposals
from appcomposer.login import current_user


class TestTranslateAjax:
    def __init__(self):
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
        app = api.get_app_by_name("UTApp")
        if app is not None:
            api.delete_app(app)

        app = api.get_app_by_name("UTApp2")
        if app is not None:
            api.delete_app(app)

        app = api.get_app_by_name("UTApp (1)")
        if app is not None:
            api.delete_app(app)

    def setUp(self):
        appcomposer.app.config['DEBUG'] = True
        appcomposer.app.config['TESTING'] = True
        appcomposer.app.config['CSRF_ENABLED'] = False
        appcomposer.app.config["SECRET_KEY"] = 'secret'
        self.flask_app = appcomposer.app.test_client()
        self.flask_app.__enter__()

        rv = self.login("testuser", "password")

        # In case the test failed before, start from a clean state.
        self._cleanup()

        # Create an App for the tests.
        self.tapp = api.create_app("UTApp", "translate", '{"spec":"http://justatest.com"}')

        # Because it's a translate app it needs an spec when it is created, and that is in fact required by some of the tests.
        api.add_var(self.tapp, "spec", "http://justatest.com")

    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

    def test_autoaccept_get(self):
        get_url = u"/composers/translate/config/autoaccept/" + self.tapp.unique_id
        rv = self.flask_app.get(get_url)

        assert rv.status_code == 200

        js = json.loads(rv.data)

        assert js["result"] == "success"
        assert js["value"] == True  # True by default.

    def test_autoaccept_not_exist(self):
        get_url = u"/composers/translate/config/autoaccept/" + "32124214124134124124"  # Non existing
        rv = self.flask_app.get(get_url)

        assert rv.status_code == 200

        js = json.loads(rv.data)

        assert js["result"] == "error"

    def test_autoaccept_post(self):

        # Check for 0 POST
        url = u"/composers/translate/config/autoaccept/" + self.tapp.unique_id
        rv = self.flask_app.post(url, data={"value": 0})
        assert rv.status_code == 200
        js = json.loads(rv.data)
        assert js["result"] == "success"
        assert js["value"] == False
        app = get_app(self.tapp.unique_id)
        appdata = json.loads(app.data)
        assert appdata["autoaccept"] == False

        # Check for 1 POST
        url = u"/composers/translate/config/autoaccept/" + self.tapp.unique_id
        rv = self.flask_app.post(url, data={"value": 1})
        assert rv.status_code == 200
        js = json.loads(rv.data)
        assert js["result"] == "success"
        assert js["value"] == True
        app = get_app(self.tapp.unique_id)
        appdata = json.loads(app.data)
        assert appdata["autoaccept"] == True

        # Check for INVALID POST
        url = u"/composers/translate/config/autoaccept/" + self.tapp.unique_id
        rv = self.flask_app.post(url, data={"value": 234124})  # Invalid value
        assert rv.status_code == 200
        js = json.loads(rv.data)
        assert js["result"] == "error"