import json
import appcomposer
import appcomposer.application

from appcomposer.tests.utils import LoggedInComposerTest
from appcomposer.appstorage import api


class TestAppstoragePersistence(LoggedInComposerTest):

    def _cleanup(self):
        """
        Does cleanup tasks in case the tests failed before.
        Can be invoked *before* and *after* the tests.
        """
        with self.client:
            self.client.get("/")  # Required so that we have a ready session
            rv = self.login("testuser", "password")
            app = api.get_app_by_name("UTApp")
            if app is not None:
                api.delete_app(app)

    def setUp(self):
        super(TestAppstoragePersistence, self).setUp()

        try:
            with self.client:
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
        except:
            self.tearDown()
            raise

    def test_created_app_persists(self):
        with self.client:
            rv = self.login("testuser", "password")
            app = api.get_app_by_name("UTApp")

            assert app is not None

            vars = api.get_all_vars(app)

            assert len(vars) == 1

            var = vars[0]

            assert var.name == "TestVar"
            assert var.value == "TestValue"





