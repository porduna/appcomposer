import appcomposer
import nose.tools as nt


class TestAppstorage:

    def setUp(self):
        appcomposer.app.config['DEBUG'] = True
        appcomposer.app.config["SECRET_KEY"] = 'secret'
        self.app = appcomposer.app.test_client()

    def tearDown(self):
        pass

    def test_root_page(self):
        rootResponse = self.app.get("/").data
        nt.assert_true("Use it!" in rootResponse)