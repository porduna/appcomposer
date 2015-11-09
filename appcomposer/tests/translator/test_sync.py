import json
from flask import request
from mock import patch
from appcomposer.login import graasp_oauth_login_redirect
from appcomposer.tests.translator.fake_requests import create_requests_mock
from appcomposer.tests.utils import ComposerTest
from appcomposer.translator.tasks import synchronize_apps_no_cache_wrapper
from appcomposer.translator.views import api_translations, api_translate, bundle_update
from appcomposer.translator.mongodb_pusher import mongo_translation_urls, mongo_bundles

class TranslatorTest(ComposerTest):
    def setUp(self):
        super(TranslatorTest, self).setUp()
        mongo_translation_urls.remove()
        mongo_bundles.remove()

    def assertAppMongoDB(self, language, url, messages):
        resultUrl = mongo_translation_urls.find_one({'_id':'{0}_ALL_ALL::http://{1}/languages/en_ALL.xml'.format(language, url)})
        resultApp = mongo_bundles.find_one({'_id':'{0}_ALL_ALL::http://{1}/gadget.xml'.format(language, url)})
        self.assertEquals(resultUrl['data'], resultApp['data'])
        data = json.loads(resultUrl['data'])
        self.assertEqual(json.dumps(data), json.dumps(messages))

    def build_dict(self, identifier, number_of_messages, prefix, last = None):
        d = {}
        for x in range(number_of_messages):
            d['message{0}_{1}'.format(x + 1, identifier)] = "{0}{1}_{2}".format(prefix, x + 1, identifier)
        if last:
            d['message{0}_{1}'.format(number_of_messages, identifier)] = "{0}{1}_{2}".format(last, number_of_messages, identifier)
        return d

    def assertMessages(self, messages, expected_messages):
        for message_key, message_value in expected_messages.items():
            message = messages[message_key]
            if message_value['can_edit']:
                self.assertTrue(messages[message_key]['can_edit'])
            else:
                self.assertFalse(messages[message_key]['can_edit'])

            if message_value['from_default']:
                self.assertTrue(messages[message_key]['from_default'])
            else:
                self.assertFalse(messages[message_key]['from_default'])

            self.assertEqual(message_value['source'], message['source'])
            self.assertEqual(message_value['target'], message['target'])

    def assertApiTranslate(self, url, lang, automatic, preview, expected_messages = None):
        request.args = {'app_url' : url}

        # Check API
        results = api_translate('{0}_ALL'.format(lang), 'ALL').json
        if automatic:
            self.assertTrue(results['automatic'])
        else:
            self.assertFalse(results['automatic'])

        if preview:
            self.assertTrue(results['preview'])
        else:
            self.assertFalse(results['preview'])

        self.assertEquals(results['url'], url)
        
        self.assertMessages(results['translation'], expected_messages)

    def assertApp1(self):
        self.assertAppMongoDB("en", "url1", self.build_dict(1, 4, "Message"))
        self.assertAppMongoDB("es", "url1", self.build_dict(1, 4, "Mensaje", "Message"))

        # Check API
        self.assertApiTranslate('http://url1/gadget.xml', lang = 'en', automatic = False, preview = True, expected_messages = {
            'message1_1': dict(can_edit=False, from_default=False, source='Message1_1', target='Message1_1'),
        })
        
        # In Spanish, the fourth message is special
        self.assertApiTranslate('http://url1/gadget.xml', lang = 'es', automatic = False, preview = True, expected_messages = {
            'message1_1': dict(can_edit=False, from_default=False, source='Message1_1', target='Mensaje1_1'),
            'message4_1': dict(can_edit=True,  from_default=True,  source='Message4_1', target='Message4_1'),
        })
        
        # There is no translation to French, so it's automatic
        self.assertApiTranslate('http://url1/gadget.xml', lang = 'fr', automatic = True, preview = True, expected_messages = {
            'message1_1': dict(can_edit=True, from_default=False, source='Message1_1', target=None),
            'message4_1': dict(can_edit=True, from_default=False, source='Message4_1', target=None),
        })

    def assertApp2(self):
        self.assertAppMongoDB("en", "url2", self.build_dict(2, 4, "NonAutomaticMessage"))
        self.assertAppMongoDB("es", "url2", self.build_dict(2, 4, "NonAutomaticMensaje", "NonAutomaticMessage"))

        # Check API
        self.assertApiTranslate('http://url2/gadget.xml', lang = 'en', automatic = False, preview = False, expected_messages = {
            'message1_2': dict(can_edit=False, from_default=False, source='NonAutomaticMessage1_2', target='NonAutomaticMessage1_2'),
        })
            
        # In Spanish, the fourth message is special
        self.assertApiTranslate('http://url2/gadget.xml', lang = 'es', automatic = False, preview = False, expected_messages = {
            'message1_2': dict(can_edit=False, from_default=False, source='NonAutomaticMessage1_2', target='NonAutomaticMensaje1_2'),
            'message4_2': dict(can_edit=True,  from_default=True,  source='NonAutomaticMessage4_2', target='NonAutomaticMessage4_2'),
        })
        
        # There is no translation to French, so it's not automatic
        self.assertApiTranslate('http://url2/gadget.xml', lang = 'fr', automatic = False, preview = False, expected_messages = {
            'message1_2': dict(can_edit=True,  from_default=False, source='NonAutomaticMessage1_2', target=None),
            'message4_2': dict(can_edit=True,  from_default=False, source='NonAutomaticMessage4_2', target=None),
        })

    def assertGraaspApp(self):
        resultEngUrl = mongo_translation_urls.find_one({'_id':'en_ALL_ALL::http://composer.golabz.eu/graasp_i18n/languages/en_ALL.xml'})
        resultEngApp = mongo_bundles.find_one({'_id':'en_ALL_ALL::http://composer.golabz.eu/graasp_i18n/'})
        self.assertEquals(resultEngUrl['data'], resultEngApp['data'])
        data = json.loads(resultEngUrl['data'])
        self.assertEquals("Message1_1", data['message1_1'])
        self.assertEquals("Message2_1", data['message2_1'])
        self.assertEquals("Message3_1", data['message3_1'])
        self.assertEquals("Message4_1", data['message4_1'])

    def assertGraaspAppNotFound(self):
        resultEngUrl = mongo_translation_urls.find_one({'_id':'en_ALL_ALL::http://composer.golabz.eu/graasp_i18n/languages/en_ALL.xml'})
        self.assertIsNone(resultEngUrl)
        resultEngApp = mongo_bundles.find_one({'_id':'en_ALL_ALL::http://composer.golabz.eu/graasp_i18n/'})
        self.assertIsNone(resultEngApp)

    def assertApps(self):
        self.assertApp1()
        self.assertApp2()


class TestSync(TranslatorTest):

    @patch("appcomposer.translator.utils.get_cached_session")
    @patch("requests.Session")
    def test_sync(self, mock_requests, mock_requests_cached_session):
        mock_requests().get = create_requests_mock()
        mock_requests_cached_session().get = create_requests_mock()

        graasp_oauth_login_redirect()
        synchronize_apps_no_cache_wrapper("testing", None)
        self.assertApps()
        self.assertGraaspApp()
        synchronize_apps_no_cache_wrapper("testing", None)
        self.assertApps()
        self.assertGraaspApp()

    @patch("appcomposer.translator.utils.get_cached_session")
    @patch("requests.Session")
    def test_sync_single_url(self, mock_requests, mock_requests_cached_session):
        mock_requests().get = create_requests_mock()
        mock_requests_cached_session().get = create_requests_mock()

        graasp_oauth_login_redirect()
        synchronize_apps_no_cache_wrapper("testing", 'http://url1/gadget.xml')
        self.assertApp1()
        self.assertGraaspAppNotFound()
        synchronize_apps_no_cache_wrapper("testing", 'http://composer.golabz.eu/graasp_i18n/')
        self.assertGraaspApp()

    @patch("appcomposer.translator.utils.get_cached_session")
    def test_sync2(self, mock):
        mock().get = create_requests_mock()
        synchronize_apps_no_cache_wrapper("testing", None)
