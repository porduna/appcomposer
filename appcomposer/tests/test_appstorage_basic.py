import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.login import current_user


class TestAppstorageBasic:

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
        app = api.get_app_by_name("UTApp")
        if app is not None:
            api.delete_app(app)
        app = api.get_app_by_name("UTAppDel")
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

        # import readline # optional, will allow Up/Down/History in the console
        # import code
        # vars = globals().copy()
        # vars.update(locals())
        # shell = code.InteractiveConsole(vars)
        # shell.interact()

    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

    def test_current_user(self):
        cu = current_user()
        assert cu.login == "testuser"

    def test_create_app(self):
        app = api.create_app("UTApp", "dummy", None, "{}")
        assert app is not None
        assert app.name == "UTApp"

        id = app.unique_id  # TODO: Probably no point for App to have two different unique ids.
        app = None
        app = api.get_app(id)
        assert app is not None
        assert app.name == "UTApp"
        assert app.owner == current_user()

    def test_delete_app(self):
        app = api.create_app("UTAppDel", "dummy", None, "{}")
        assert app is not None

        api.delete_app(app)
        app = api.get_app_by_name("UTAppDel")
        assert app is None