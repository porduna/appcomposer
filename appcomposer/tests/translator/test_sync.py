import json
from flask import request
from mock import patch
from appcomposer.login import graasp_oauth_login_redirect
from appcomposer.tests.translator.fake_requests import create_requests_mock
from appcomposer.tests.utils import ComposerTest
from appcomposer.translator.tasks import synchronize_apps_no_cache_wrapper
from appcomposer.translator.views import api_translations2, api_translate
from appcomposer.translator.mongodb_pusher import mongo_translation_urls, mongo_bundles

class TranslatorTest(ComposerTest):
    def setUp(self):
        super(TranslatorTest, self).setUp()
        mongo_translation_urls.remove()
        mongo_bundles.remove()

    def assertApp1(self):
        # Check MongoDB (English and Spanish)
        resultEngUrl = mongo_translation_urls.find_one({'_id':'en_ALL_ALL::http://url1/languages/en_ALL.xml'})
        resultEngApp = mongo_bundles.find_one({'_id':'en_ALL_ALL::http://url1/gadget.xml'})
        self.assertEquals(resultEngUrl['data'], resultEngApp['data'])
        data = json.loads(resultEngUrl['data'])
        self.assertEquals("Message1_1", data['message1_1'])
        self.assertEquals("Message2_1", data['message2_1'])
        self.assertEquals("Message3_1", data['message3_1'])
        self.assertEquals("Message4_1", data['message4_1'])

        resultSpaUrl = mongo_translation_urls.find_one({'_id':'es_ALL_ALL::http://url1/languages/en_ALL.xml'})
        resultSpaApp = mongo_bundles.find_one({'_id':'es_ALL_ALL::http://url1/gadget.xml'})
        self.assertEquals(resultSpaUrl['data'], resultSpaApp['data'])
        data = json.loads(resultSpaUrl['data'])

        self.assertEquals("Mensaje1_1", data['message1_1'])
        self.assertEquals("Mensaje2_1", data['message2_1'])
        self.assertEquals("Mensaje3_1", data['message3_1'])
        # This is self-filled by its English version
        self.assertEquals("Message4_1", data['message4_1'])

        request.args = {'app_url' : 'http://url1/gadget.xml'}

        # Check API
        english_results = api_translate('en_ALL', 'ALL').json
        self.assertFalse(english_results['automatic'])
        self.assertEquals(english_results['url'], 'http://url1/gadget.xml')
        message1_1 = english_results['translation']['message1_1']
        self.assertFalse(message1_1['can_edit'])
        self.assertFalse(message1_1['from_default'])
        self.assertEquals("Message1_1", message1_1['source'])
        self.assertEquals("Message1_1", message1_1['target'])
            
        # In Spanish, the fourth message is special
        spanish_results = api_translate('es_ALL', 'ALL').json
        self.assertFalse(spanish_results['automatic'])
        self.assertEquals(spanish_results['url'], 'http://url1/gadget.xml')
        message1_1 = spanish_results['translation']['message1_1']
        self.assertFalse(message1_1['can_edit'])
        self.assertFalse(message1_1['from_default'])
        self.assertEquals("Message1_1", message1_1['source'])
        self.assertEquals("Mensaje1_1", message1_1['target'])
        message4_1 = spanish_results['translation']['message4_1']
        self.assertTrue(message4_1['can_edit'])
        self.assertTrue(message4_1['from_default'])
        self.assertEquals("Message4_1", message4_1['source'])
        self.assertEquals("Message4_1", message4_1['target'])
        
        # There is no translation to French, so it's automatic
        french_results = api_translate('fr_ALL', 'ALL').json
        french_results = api_translate('fr_ALL', 'ALL').json
        # TODO: this is a bug!
        self.assertTrue(french_results['automatic'])
        self.assertEquals(french_results['url'], 'http://url1/gadget.xml')
        message1_1 = french_results['translation']['message1_1']
        self.assertTrue(message1_1['can_edit'])
        self.assertFalse(message1_1['from_default'])
        self.assertEquals("Message1_1", message1_1['source'])
        self.assertIsNone(message1_1['target'])
        message4_1 = french_results['translation']['message4_1']
        self.assertTrue(message4_1['can_edit'])
        self.assertFalse(message4_1['from_default'])
        self.assertEquals("Message4_1", message4_1['source'])
        self.assertIsNone(message4_1['target'])

    def assertApps(self):
        self.assertApp1()


class TestSync(TranslatorTest):
    @patch("appcomposer.translator.utils.get_cached_session")
    @patch("requests.Session")
    def test_sync(self, mock_requests, mock_requests_cached_session):
        mock_requests().get = create_requests_mock()
        mock_requests_cached_session().get = create_requests_mock()

        graasp_oauth_login_redirect()
        synchronize_apps_no_cache_wrapper(None)
        self.assertApps()
        synchronize_apps_no_cache_wrapper(None)
        self.assertApps()


    @patch("appcomposer.translator.utils.get_cached_session")
    def test_sync2(self, mock):
        mock().get = create_requests_mock()
        synchronize_apps_no_cache_wrapper(None)
