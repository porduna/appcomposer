import json
from mock import patch
from appcomposer.login import graasp_oauth_login_redirect
from appcomposer.tests.translator.fake_requests import create_requests_mock
from appcomposer.tests.utils import ComposerTest
from appcomposer.translator.tasks import synchronize_apps_no_cache_wrapper
from appcomposer.translator.views import api_translations2
from appcomposer.translator.mongodb_pusher import mongo_translation_urls, mongo_bundles

class TranslatorTest(ComposerTest):
    def setUp(self):
        super(TranslatorTest, self).setUp()
        mongo_translation_urls.remove()
        mongo_bundles.remove()

    def assertApp1(self):
        resultEngUrl = mongo_translation_urls.find_one({'_id':'en_ALL_ALL::http://url1/languages/en_ALL.xml'})
        resultEngApp = mongo_bundles.find_one({'_id':'en_ALL_ALL::http://url1/gadget.xml'})
        self.assertEquals(resultEngUrl['data'], resultEngApp['data'])
        data = json.loads(resultEngUrl['data'])
        self.assertEquals('Message1_1', data['message1_1'])
        self.assertEquals('Message2_1', data['message2_1'])
        self.assertEquals('Message3_1', data['message3_1'])
        self.assertEquals('Message4_1', data['message4_1'])

        resultSpaUrl = mongo_translation_urls.find_one({'_id':'es_ALL_ALL::http://url1/languages/en_ALL.xml'})
        resultSpaApp = mongo_bundles.find_one({'_id':'es_ALL_ALL::http://url1/gadget.xml'})
        self.assertEquals(resultSpaUrl['data'], resultSpaApp['data'])
        data = json.loads(resultSpaUrl['data'])

        self.assertEquals('Mensaje1_1', data['message1_1'])
        self.assertEquals('Mensaje2_1', data['message2_1'])
        self.assertEquals('Mensaje3_1', data['message3_1'])
        # This is self-filled by its English version
        self.assertEquals('Message4_1', data['message4_1'])


class TestSync(TranslatorTest):
    @patch("appcomposer.translator.utils.get_cached_session")
    @patch("requests.Session")
    def test_sync(self, mock_requests, mock_requests_cached_session):
        mock_requests().get = create_requests_mock()
        mock_requests_cached_session().get = create_requests_mock()

        graasp_oauth_login_redirect()
        synchronize_apps_no_cache_wrapper(None)
        self.assertApp1()


    @patch("appcomposer.translator.utils.get_cached_session")
    def test_sync2(self, mock):
        mock().get = create_requests_mock()
        synchronize_apps_no_cache_wrapper(None)
