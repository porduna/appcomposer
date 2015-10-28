import appcomposer
from appcomposer.tests.utils import ComposerTest
import nose.tools as nt


class TestBasic(ComposerTest):
    def test_root_page(self):
        rootResponse = self.client.get("/").data
        nt.assert_true("Go-Lab App Composer" in rootResponse)

    def test_about_page(self):
        rv = self.client.get("/about")
        assert rv.status_code == 200
