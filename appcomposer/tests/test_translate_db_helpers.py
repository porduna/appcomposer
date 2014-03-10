import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.composers.translate.db_helpers import _db_declare_ownership
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

    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

    def test_current_user(self):
        cu = current_user()
        assert cu.login == "testuser"

    def test_declare_ownership(self):
        _db_declare_ownership(self.tapp, "test_TEST")

        vars = api.get_all_vars(self.tapp)
        var = vars[0]
        assert var.name == "ownership"
        assert var.value == "test_TEST"

    def test_get_lang_owner_app(self):
        _db_declare_ownership(self.tapp, "test_TEST")
        # owner = _db_get_lang_owner_app(spec, )
        # TODO: Continue this.