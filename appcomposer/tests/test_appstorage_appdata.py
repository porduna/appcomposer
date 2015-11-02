import json
import appcomposer
import appcomposer.application
from appcomposer.tests.utils import AppCreatedComposerTest

from appcomposer.appstorage import api


class TestAppstorageAppvars(AppCreatedComposerTest):
    def _cleanup(self):
        """
        Does cleanup tasks in case the tests failed before.
        Can be invoked *before* and *after* the tests.
        """
        app = api.get_app_by_name("UTApp")
        if app is not None:
            api.delete_app(app)

    def test_data_empty(self):
        assert self.tapp.data == "{}"

    def test_data_save(self):
        data = {"MYNAME": "TEST"}
        api.update_app_data(self.tapp, json.dumps(data))

        recdata = api.get_app_by_name("UTApp").data
        pdata = json.loads(recdata)

        assert data == pdata
