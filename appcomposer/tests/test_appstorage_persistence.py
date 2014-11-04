import json
import appcomposer
import appcomposer.application

from appcomposer.appstorage import api


class TestAppstoragePersistence:

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
        self.flask_app = appcomposer.app.test_client()
        with self.flask_app:
            self.flask_app.get("/")  # Required so that we have a ready session
            rv = self.login("testuser", "password")
            app = api.get_app_by_name("UTApp")
            if app is not None:
                api.delete_app(app)

    def setUp(self):
        appcomposer.app.config['DEBUG'] = True
        appcomposer.app.config['TESTING'] = True
        appcomposer.app.config['CSRF_ENABLED'] = False
        appcomposer.app.config["SECRET_KEY"] = 'secret'

        self._cleanup()

        self.flask_app = appcomposer.app.test_client()
        with self.flask_app:
            rv = self.login("testuser", "password")

            # import readline # optional, will allow Up/Down/History in the console
            # import code
            # vars = globals().copy()
            # vars.update(locals())
            # shell = code.InteractiveConsole(vars)
            # shell.interact()

            # Create an App for the tests.
            self.tapp = api.create_app("UTApp", "dummy", None, "{}")
            self.tapp = api.get_app_by_name("UTApp")
            api.set_var(self.tapp, "TestVar", "TestValue")


    def tearDown(self):
        self._cleanup()

    def test_created_app_persists(self):
        self.flask_app = appcomposer.app.test_client()
        with self.flask_app:
            rv = self.login("testuser", "password")
            app = api.get_app_by_name("UTApp")

            assert app is not None

            vars = api.get_all_vars(app)

            assert len(vars) == 1

            var = vars[0]

            assert var.name == "TestVar"
            assert var.value == "TestValue"





