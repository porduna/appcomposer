import json
from flask import request
from mock import patch
import appcomposer.translator.translation_listing as trlisting
from appcomposer.login import graasp_oauth_login_redirect
from appcomposer.tests.translator.fake_requests import create_requests_mock
from appcomposer.tests.utils import ComposerTest
from appcomposer.translator.tasks import synchronize_apps_no_cache_wrapper, task_synchronize_single_app
from appcomposer.views.api import api_translate, bundle_update
from appcomposer.translator.mongodb_pusher import mongo_translation_urls, mongo_bundles, sync

class TranslatorTest(ComposerTest):
    def setUp(self):
        trlisting.DEBUG_VERBOSE = False
        super(TranslatorTest, self).setUp()
        mongo_translation_urls.remove()
        mongo_bundles.remove()

    def assertAppMongoDB(self, language, url, messages, messages_prefix = ''):
        resultUrl = mongo_translation_urls.find_one({'_id':'{0}_ALL_ALL::http://{1}/languages/{2}en_ALL.xml'.format(language, url, messages_prefix)})
        resultApp = mongo_bundles.find_one({'_id':'{0}_ALL_ALL::http://{1}/{2}gadget.xml'.format(language, url, messages_prefix)})
        self.assertIsNotNone(resultUrl)
        self.assertIsNotNone(resultApp)
        self.assertEquals(resultUrl['data'], resultApp['data'])
        data = json.loads(resultUrl['data'])
        self.assertEqual(json.dumps(data), json.dumps(messages))
        # self.assertDictEqual(data, messages)

    def build_dict(self, identifier, number_of_messages, prefix, last = None, exceptions = None):
        d = {}
        for x in range(number_of_messages):
            d['message{0}_{1}'.format(x + 1, identifier)] = "{0}{1}_{2}".format(prefix, x + 1, identifier)
        if last:
            d['message{0}_{1}'.format(number_of_messages, identifier)] = "{0}{1}_{2}".format(last, number_of_messages, identifier)
        if exceptions:
            for exception_key, exception_value in exceptions.items():
                d[exception_key] = exception_value
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

    def assertApiTranslate(self, url, lang, automatic, preview, expected_messages = None, unexpected_messages = None):
        request.args = {'app_url' : url}

        # Check API
        results = api_translate('{0}_ALL'.format(lang), 'ALL').json
        self.assertIn('automatic', results)
        if automatic:
            self.assertTrue(results['automatic'])
        else:
            self.assertFalse(results['automatic'])

        self.assertIn('preview', results)
        if preview:
            self.assertTrue(results['preview'])
        else:
            self.assertFalse(results['preview'])

        self.assertEquals(results['url'], url)
        
        self.assertMessages(results['translation'], expected_messages)

        if unexpected_messages:
            for unexpected_key in unexpected_messages:
                self.assertNotIn(unexpected_key, results['translation'])

    def assertApp1(self):
        self.assertAppMongoDB("en", "url1", self.build_dict(1, 4, "Message"))
        self.assertAppMongoDB("es", "url1", self.build_dict(1, 4, "Mensaje", "Message"))

        # Check API
        self.assertApiTranslate('http://url1/gadget.xml', lang = 'en', automatic = False, preview = True, expected_messages = {
            'message1_1': dict(can_edit=False, from_default=True, source='Message1_1', target='Message1_1'),
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
            'message1_2': dict(can_edit=False, from_default=True, source='NonAutomaticMessage1_2', target='NonAutomaticMessage1_2'),
        })
            
        # In Spanish, the fourth message is special
        self.assertApiTranslate('http://url2/gadget.xml', lang = 'es', automatic = False, preview = False, expected_messages = {
            'message1_2': dict(can_edit=False, from_default=False, source='NonAutomaticMessage1_2', target='NonAutomaticMensaje1_2'),
            'message4_2': dict(can_edit=True,  from_default=True,  source='NonAutomaticMessage4_2', target='NonAutomaticMessage4_2'),
        })
        
        # There is no translation to French, but it's still not automatic
        self.assertApiTranslate('http://url2/gadget.xml', lang = 'fr', automatic = False, preview = False, expected_messages = {
            'message1_2': dict(can_edit=True, from_default=False, source='NonAutomaticMessage1_2', target=None),
            'message4_2': dict(can_edit=True, from_default=False, source='NonAutomaticMessage4_2', target=None),
        })

    def assertApp3before(self):
        # url3 hosts 2 apps, with some shared terms.
        # messages 1 and 2 are "common". message 3 is of a third tool. message 4 is of tool_. messages 5 and 6 are not of any tool (and therefore, they're of all)

        # First we test the first app (tool_, so messages 4, 5 and 6 apply)

        self.assertAppMongoDB("en", "url3", self.build_dict(3, 6, "ToolIdMessage"), 'tool_')
        self.assertAppMongoDB("es", "url3", self.build_dict(3, 6, "ToolIdMensaje", "ToolIdMessage"), 'tool_')

        # Check API
        self.assertApiTranslate('http://url3/tool_gadget.xml', lang = 'en', automatic = False, preview = True, expected_messages = {
            'message4_3': dict(can_edit=False, from_default=True, source='ToolIdMessage4_3', target='ToolIdMessage4_3'),
            'message5_3': dict(can_edit=False, from_default=True, source='ToolIdMessage5_3', target='ToolIdMessage5_3'),
            'message6_3': dict(can_edit=False, from_default=True, source='ToolIdMessage6_3', target='ToolIdMessage6_3'),
        }, unexpected_messages = ('message1_3', 'message2_3', 'message3_3')) # unexpected: those in common or other tools

        # In Spanish, the sixth message is special
        self.assertApiTranslate('http://url3/tool_gadget.xml', lang = 'es', automatic = False, preview = True, expected_messages = {
            'message4_3': dict(can_edit=False, from_default=False, source='ToolIdMessage4_3', target='ToolIdMensaje4_3'),
            'message5_3': dict(can_edit=False, from_default=False, source='ToolIdMessage5_3', target='ToolIdMensaje5_3'),
            'message6_3': dict(can_edit=True,  from_default=True, source='ToolIdMessage6_3', target='ToolIdMessage6_3'),
        }, unexpected_messages = ('message1_3', 'message2_3', 'message3_3')) # unexpected: those in common or other tools

        # There is no translation to French, so it's automatic
        self.assertApiTranslate('http://url3/tool_gadget.xml', lang = 'fr', automatic = True, preview = True, expected_messages = {
            'message4_3': dict(can_edit=True, from_default=False, source='ToolIdMessage4_3', target=None),
            'message5_3': dict(can_edit=True, from_default=False, source='ToolIdMessage5_3', target=None),
            'message6_3': dict(can_edit=True, from_default=False, source='ToolIdMessage6_3', target=None),
        }, unexpected_messages = ('message1_3', 'message2_3', 'message3_3')) # unexpected: those in common or other tools

        # 
        # Then we test the second one (common_, so messages 1, 2, 5 and 6 apply)
        # 
        self.assertAppMongoDB("en", "url3", self.build_dict(3, 6, "ToolIdMessage"), 'common_')
        self.assertAppMongoDB("es", "url3", self.build_dict(3, 6, "ToolIdMensaje", "ToolIdMessage"), 'common_')

        self.assertApiTranslate('http://url3/common_gadget.xml', lang = 'en', automatic = False, preview = True, expected_messages = {
            'message1_3': dict(can_edit=False, from_default=True, source='ToolIdMessage1_3', target='ToolIdMessage1_3'),
            'message2_3': dict(can_edit=False, from_default=True, source='ToolIdMessage2_3', target='ToolIdMessage2_3'),
            'message5_3': dict(can_edit=False, from_default=True, source='ToolIdMessage5_3', target='ToolIdMessage5_3'),
            'message6_3': dict(can_edit=False, from_default=True, source='ToolIdMessage6_3', target='ToolIdMessage6_3'),
        }, unexpected_messages = ('message3_3', 'message4_3')) # unexpected: those in common or other tools

        self.assertApiTranslate('http://url3/common_gadget.xml', lang = 'es', automatic = False, preview = True, expected_messages = {
            'message1_3': dict(can_edit=False, from_default=False, source='ToolIdMessage1_3', target='ToolIdMensaje1_3'),
            'message2_3': dict(can_edit=False, from_default=False, source='ToolIdMessage2_3', target='ToolIdMensaje2_3'),
            'message5_3': dict(can_edit=False, from_default=False, source='ToolIdMessage5_3', target='ToolIdMensaje5_3'),
            'message6_3': dict(can_edit=True,  from_default=True,  source='ToolIdMessage6_3', target='ToolIdMessage6_3'),
        }, unexpected_messages = ('message3_3', 'message4_3')) # unexpected: those in common or other tools

        self.assertApiTranslate('http://url3/common_gadget.xml', lang = 'fr', automatic = True, preview = True, expected_messages = {
            'message1_3': dict(can_edit=True, from_default=False, source='ToolIdMessage1_3', target=None),
            'message2_3': dict(can_edit=True, from_default=False, source='ToolIdMessage2_3', target=None),
            'message5_3': dict(can_edit=True, from_default=False, source='ToolIdMessage5_3', target=None),
            'message6_3': dict(can_edit=True, from_default=False, source='ToolIdMessage6_3', target=None),
        }, unexpected_messages = ('message3_3', 'message4_3')) # unexpected: those in common or other tools

    def assertApp3after(self):
        # url3 hosts 2 apps, with some shared terms.
        # messages 1 and 2 are "common". message 3 is of a third tool. message 4 is of tool_. messages 5 and 6 are not of any tool (and therefore, they're of all)

        # First we test the first app (tool_, so messages 4, 5 and 6 apply)

        self.assertAppMongoDB("en", "url3", self.build_dict(3, 6, "ToolIdMessage"), 'tool_')
        self.assertAppMongoDB("es", "url3", self.build_dict(3, 6, "ToolIdMensaje", "ToolIdMessage"), 'tool_')
        self.assertAppMongoDB("fr", "url3", self.build_dict(3, 6, "ToolIdMessage", exceptions = {
            "message1_3": "TESTING_MESSAGE1", # From commons
            "message5_3": "TESTING_MESSAGE5", # From tools
        }), 'tool_')

        # Check API
        self.assertApiTranslate('http://url3/tool_gadget.xml', lang = 'en', automatic = False, preview = True, expected_messages = {
            'message4_3': dict(can_edit=False, from_default=True, source='ToolIdMessage4_3', target='ToolIdMessage4_3'),
            'message5_3': dict(can_edit=False, from_default=True, source='ToolIdMessage5_3', target='ToolIdMessage5_3'),
            'message6_3': dict(can_edit=False, from_default=True, source='ToolIdMessage6_3', target='ToolIdMessage6_3'),
        }, unexpected_messages = ('message1_3', 'message2_3', 'message3_3')) # unexpected: those in common or other tools

        # In Spanish, the sixth message is special
        self.assertApiTranslate('http://url3/tool_gadget.xml', lang = 'es', automatic = False, preview = True, expected_messages = {
            'message4_3': dict(can_edit=False, from_default=False, source='ToolIdMessage4_3', target='ToolIdMensaje4_3'),
            'message5_3': dict(can_edit=False, from_default=False, source='ToolIdMessage5_3', target='ToolIdMensaje5_3'),
            'message6_3': dict(can_edit=True,  from_default=True, source='ToolIdMessage6_3', target='ToolIdMessage6_3'),
        }, unexpected_messages = ('message1_3', 'message2_3', 'message3_3')) # unexpected: those in common or other tools

        # There is no translation to French, so it's automatic
        self.assertApiTranslate('http://url3/tool_gadget.xml', lang = 'fr', automatic = True, preview = True, expected_messages = {
            'message4_3': dict(can_edit=True, from_default=True,  source='ToolIdMessage4_3', target="ToolIdMessage4_3"),
            'message5_3': dict(can_edit=True, from_default=False, source='ToolIdMessage5_3', target="TESTING_MESSAGE5"),
            'message6_3': dict(can_edit=True, from_default=True,  source='ToolIdMessage6_3', target="ToolIdMessage6_3"),
        }, unexpected_messages = ('message1_3', 'message2_3', 'message3_3')) # unexpected: those in common or other tools

        # 
        # Then we test the second one (common_, so messages 1, 2, 5 and 6 apply)
        self.assertAppMongoDB("en", "url3", self.build_dict(3, 6, "ToolIdMessage"), 'common_')
        self.assertAppMongoDB("es", "url3", self.build_dict(3, 6, "ToolIdMensaje", "ToolIdMessage"), 'common_')
        self.assertAppMongoDB("fr", "url3", self.build_dict(3, 6, "ToolIdMessage", exceptions = {
            "message1_3": "TESTING_MESSAGE1", # From commons
        }), 'common_')

        self.assertApiTranslate('http://url3/common_gadget.xml', lang = 'en', automatic = False, preview = True, expected_messages = {
            'message1_3': dict(can_edit=False, from_default=True, source='ToolIdMessage1_3', target='ToolIdMessage1_3'),
            'message2_3': dict(can_edit=False, from_default=True, source='ToolIdMessage2_3', target='ToolIdMessage2_3'),
            'message5_3': dict(can_edit=False, from_default=True, source='ToolIdMessage5_3', target='ToolIdMessage5_3'),
            'message6_3': dict(can_edit=False, from_default=True, source='ToolIdMessage6_3', target='ToolIdMessage6_3'),
        }, unexpected_messages = ('message3_3', 'message4_3')) # unexpected: those in common or other tools

        self.assertApiTranslate('http://url3/common_gadget.xml', lang = 'es', automatic = False, preview = True, expected_messages = {
            'message1_3': dict(can_edit=False, from_default=False, source='ToolIdMessage1_3', target='ToolIdMensaje1_3'),
            'message2_3': dict(can_edit=False, from_default=False, source='ToolIdMessage2_3', target='ToolIdMensaje2_3'),
            'message5_3': dict(can_edit=False, from_default=False, source='ToolIdMessage5_3', target='ToolIdMensaje5_3'),
            'message6_3': dict(can_edit=True,  from_default=True,  source='ToolIdMessage6_3', target='ToolIdMessage6_3'),
        }, unexpected_messages = ('message3_3', 'message4_3')) # unexpected: those in common or other tools

        self.assertApiTranslate('http://url3/common_gadget.xml', lang = 'fr', automatic = True, preview = True, expected_messages = {
            'message1_3': dict(can_edit=True, from_default=False, source='ToolIdMessage1_3', target="TESTING_MESSAGE1"),
            'message2_3': dict(can_edit=True, from_default=True,  source='ToolIdMessage2_3', target="ToolIdMessage2_3"),
            'message5_3': dict(can_edit=True, from_default=True,  source='ToolIdMessage5_3', target="ToolIdMessage5_3"),
            'message6_3': dict(can_edit=True, from_default=True,  source='ToolIdMessage6_3', target="ToolIdMessage6_3"),
        }, unexpected_messages = ('message3_3', 'message4_3')) # unexpected: those in common or other tools



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

    def assertApps(self, before = True):
        self.assertApp1()
        self.assertApp2()
        if before:
            self.assertApp3before()
        else:
            self.assertApp3after()


class TestSync(TranslatorTest):

    @patch("appcomposer.translator.utils.get_cached_session")
    @patch("requests.Session")
    def test_sync(self, mock_requests, mock_requests_cached_session):
        mock_requests().get = create_requests_mock()
        mock_requests_cached_session().get = create_requests_mock()

        graasp_oauth_login_redirect()
        synchronize_apps_no_cache_wrapper("testing")
        self.assertApps()
        self.assertGraaspApp()

        synchronize_apps_no_cache_wrapper("testing")
        self.assertApps(before = True)
        self.assertGraaspApp()

        # Add to commons one term which should be applied to tools too.
        request._cached_json = request.values = {
            'app_url': "http://url3/common_gadget.xml",
            'key': 'message1_3',
            'value': 'TESTING_MESSAGE1',
        }
        bundle_update('fr_ALL', 'ALL')

        # Add to tool_ one term which should not be applied to common.
        request._cached_json = request.values = {
            'app_url': "http://url3/tool_gadget.xml",
            'key': 'message5_3',
            'value': 'TESTING_MESSAGE5',
        }
        bundle_update('fr_ALL', 'ALL')

        sync(None, only_recent = True)

        self.assertApps(before = False)
        self.assertGraaspApp()




    @patch("appcomposer.translator.utils.get_cached_session")
    @patch("requests.Session")
    def test_sync_single_url(self, mock_requests, mock_requests_cached_session):
        mock_requests().get = create_requests_mock()
        mock_requests_cached_session().get = create_requests_mock()

        graasp_oauth_login_redirect()
        task_synchronize_single_app("testing", 'http://url1/gadget.xml')
        self.assertApp1()
        self.assertGraaspAppNotFound()
        task_synchronize_single_app("testing", 'http://composer.golabz.eu/graasp_i18n/')
        self.assertGraaspApp()

    @patch("appcomposer.translator.utils.get_cached_session")
    def test_sync2(self, mock):
        mock().get = create_requests_mock()
        synchronize_apps_no_cache_wrapper("testing")

