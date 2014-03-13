import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.composers.translate.db_helpers import _db_declare_ownership, _db_get_lang_owner_app, _db_get_ownerships, _find_unique_name_for_app, _db_get_proposals
from appcomposer.login import current_user


class TestTranslateDbHelpers:
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
        self.tapp = api.create_app("UTApp", "translate", "{'spec':'http://justatest.com'}")

        # Because it's a translate app it needs an spec when it is created, and that is in fact required by some of the tests.
        api.add_var(self.tapp, "spec", "http://justatest.com")

    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

    def test_current_user(self):
        cu = current_user()
        assert cu.login == "testuser"

    def test_declare_ownership(self):
        _db_declare_ownership(self.tapp, "test_TEST")

        vars = api.get_all_vars(self.tapp)
        var = next(var for var in vars if var.name == "ownership")
        assert var.name == "ownership"
        assert var.value == "test_TEST"

    def test_get_lang_owner_app(self):
        _db_declare_ownership(self.tapp, "test_TEST")
        owner_app = _db_get_lang_owner_app("http://justatest.com", "test_TEST")
        assert owner_app == self.tapp

    def test_get_ownerships(self):

        # There should be no ownerships declared on the spec.
        ownerships = _db_get_ownerships("http://justatest.com")
        assert len(ownerships) == 0

        # We now declare 1 ownership.
        _db_declare_ownership(self.tapp, "test_TEST")
        ownerships = _db_get_ownerships("http://justatest.com")
        assert len(ownerships) == 1

        # We now create a second app for further testing.
        app2 = api.create_app("UTApp2", "translate", "{'spec':'http://justatest.com'}")
        api.add_var(app2, "spec", "http://justatest.com")

        # Ensure we still have 1 ownership.
        ownerships = _db_get_ownerships("http://justatest.com")
        assert len(ownerships) == 1

        # Add a second ownership for another language.
        _db_declare_ownership(app2, "testen_TESTEN")
        ownerships = _db_get_ownerships("http://justatest.com")
        assert len(ownerships) == 2

        # Ensure that the ownerships are right.
        firstOwnership = next(o for o in ownerships if o.value == "test_TEST")
        assert firstOwnership.app == self.tapp
        secondOwnership = next(o for o in ownerships if o.value == "testen_TESTEN")
        assert secondOwnership.app == app2

    def test_find_unique_name_for_app(self):
        # There is no conflict, so the name should be exactly the chosen one.
        name = _find_unique_name_for_app("UTAPPDoesntExist")
        assert name == "UTAPPDoesntExist"

        # There is a conflict, so the name should include a number, starting at 1.
        name = _find_unique_name_for_app("UTApp")
        assert name == "UTApp (1)"

        # We create a new app so that we can force a second conflict.
        app2 = api.create_app("UTApp (1)", "translate", "{'spec':'http://justatest.com'}")
        api.add_var(app2, "spec", "http://justatest.com")
        name = _find_unique_name_for_app("UTApp")
        assert name == "UTApp (2)"

    def test_get_proposals(self):

        proposals = _db_get_proposals(self.tapp)
        len(proposals) == 0

        # We add a fake proposal for the test app we have.
        # The data for the proposal is NOT valid, but shouldn't affect this test.
        api.add_var(self.tapp, "proposal", "{}")
        api.add_var(self.tapp, "proposal", "{}")
        proposals = _db_get_proposals(self.tapp)
        assert len(proposals) == 2