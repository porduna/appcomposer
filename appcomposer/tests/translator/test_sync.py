from mock import patch
from appcomposer.tests.translator.fake_requests import create_requests_mock
from appcomposer.translator.tasks import synchronize_apps_no_cache_wrapper

class TestSync:
    @patch("appcomposer.translator.utils.get_cached_session")
    def test_sync(self, mock):
        mock.side_effect = lambda : create_requests_mock()
        # synchronize_apps_no_cache_wrapper(None)
