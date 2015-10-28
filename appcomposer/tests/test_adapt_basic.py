import appcomposer
import appcomposer.application
from appcomposer.tests.utils import ComposerTest


class TestBasicAdaptApp(ComposerTest):
    """
    Test the initial adapt screen.
    """
    def test_adapt_index(self):
        """
        Ensure that the index page is what we expect.
        """
        self.login()
        # Ensure that the index page is what we expect. The page to choose the URL, etc.
        rv = self.client.get("/composers/adapt/")
        print "DATA: " + rv.data
        assert rv.status_code == 200
        assert "Choose" in rv.data
        assert "configstore" in rv.data
