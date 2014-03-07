import appcomposer
import appcomposer.application

from appcomposer.appstorage import api
from appcomposer.login import current_user


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

    def tearDown(self):
        self._cleanup()
        self.flask_app.__exit__(None, None, None)

    def test_current_user(self):
        cu = current_user()
        assert cu.login == "testuser"

    def test_add_get_var(self):
        api.add_var(self.tapp, "TestVar", "TestValue")
        vars = api.get_all_vars(self.tapp)

        assert len(vars) == 1
        myvar = vars[0]
        assert myvar.name == "TestVar"
        assert myvar.value == "TestValue"

    def test_add_get_several_var(self):
        api.add_var(self.tapp, "TestVar1", "TestValue1")
        api.add_var(self.tapp, "TestVar2", "TestValue2")
        api.add_var(self.tapp, "TestVar3", "TestValue3")

        vars = api.get_all_vars(self.tapp)

        assert len(vars) == 3

        kvdict = {var.name: var.value for var in vars}
        assert kvdict["TestVar1"] == "TestValue1"
        assert kvdict["TestVar2"] == "TestValue2"
        assert kvdict["TestVar3"] == "TestValue3"

    def test_delete_var(self):
        api.add_var(self.tapp, "TestVar1", "TestValue1")
        api.add_var(self.tapp, "TestVar2", "TestValue2")
        api.add_var(self.tapp, "TestVar3", "TestValue3")

        vars = api.get_all_vars(self.tapp)

        # Find the var with the name.
        api.remove_var(next(var for var in vars if var.name == "TestVar1"))

        vars = api.get_all_vars(self.tapp)

        assert len(vars) == 2

        kvdict = {var.name: var.value for var in vars}
        assert kvdict["TestVar2"] == "TestValue2"
        assert kvdict["TestVar3"] == "TestValue3"

    def test_update_var(self):
        var = api.add_var(self.tapp, "TestVar1", "TestValue1")

        assert var.value == "TestValue1"

        api.set_var(self.tapp, "TestVar1", "NewValue")
        assert var.value == "NewValue"

    def test_same_name_supported(self):
        api.add_var(self.tapp, "TestVar1", "TestValue1")
        api.add_var(self.tapp, "TestVar1", "TestValue2")
        api.add_var(self.tapp, "TestVar1", "TestValue3")

        vars = api.get_all_vars(self.tapp)

        assert len(vars) == 3