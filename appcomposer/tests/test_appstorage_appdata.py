import json
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api


class TestAppstorageAppvars:

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

        # import readline # optional, will allow Up/Down/History in the console
        # import code
        # vars = globals().copy()
        # vars.update(locals())
        # shell = code.InteractiveConsole(vars)
        # shell.interact()

        # Create an App for the tests.
        self.tapp = api.create_app("UTApp", "dummy", "{}")

        self.tapp = api.get_app_by_name("UTApp")

    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

    def test_data_empty(self):
        assert self.tapp.data == "{}"

    def test_data_save(self):
        data = {"MYNAME": "TEST"}
        api.update_app_data(self.tapp, json.dumps(data))

        recdata = api.get_app_by_name("UTApp").data
        pdata = json.loads(recdata)

        assert data == pdata
