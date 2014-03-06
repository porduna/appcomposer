import json
from appcomposer.appstorage import create_app
from appcomposer.appstorage.api import delete_app, get_app

import appcomposer


class TestTranslateDbHelpers:

    def __init__(self):
        self.app = None

    def setUp(self):
        appdata = {"spec": "test.xml"}
        self.app = create_app("TestApp", "translate", json.dumps(appdata))

    def tearDown(self):
        delete_app(self.app)

    def test_get_works(self):
        appid = self.app.unique_id
        app = get_app(appid)
        assert app is not None