import json
import zlib
import logging
import urlparse
import xml.etree.ElementTree as ET

import requests

from appcomposer import redis_store
from appcomposer.exceptions import TranslatorError
from appcomposer.translator.utils import get_cached_session, fromstring, get_text_from_response

DEBUG = True

def extract_local_translations_url(app_url, force_local_cache = False):
    redis_key = 'appcomposer:fast-cache:{}'.format(app_url)

    if force_local_cache:
        # Under some situations (e.g., updating a single message), it is better to have a cache
        # than contacting the foreign server. Only if requested, this method will try to check
        # in a local cache in Redis.
        cached = redis_store.get(redis_key)
        if cached:
            translation_url, original_messages, metadata = json.loads(cached)
            if metadata is not None:
                original_messages_loaded = json.loads(original_messages)
                metadata_loaded = json.loads(metadata)
                return translation_url, original_messages_loaded, metadata_loaded

    cached_requests = get_cached_session()

    locales, _ = _extract_locales(app_url, cached_requests)

    locales_without_lang = [ locale for locale in locales if 'lang' not in locale.attrib or locale.attrib['lang'].lower() == 'all' ]
    if not locales_without_lang:
        raise TranslatorError("That application does not provide any default locale. The application has probably not been adopted to be translated.")

    relative_translation_url = locales_without_lang[0].attrib.get('messages')
    if not relative_translation_url:
        raise TranslatorError("Default Locale not provided message attribute")

    absolute_translation_url, messages, metadata, contents = _retrieve_messages_from_relative_url(app_url, relative_translation_url, cached_requests)

    redis_value = json.dumps([
        absolute_translation_url,
        json.dumps(messages),
        json.dumps(metadata)
    ])
    redis_store.setex(name=redis_key, time=10 * 60, value=redis_value) # For 10 minutes
    return absolute_translation_url, messages, metadata

def extract_metadata_information(app_url, cached_requests = None, force_reload = False):
    if cached_requests is None:
        cached_requests = get_cached_session()

    locales, body = _extract_locales(app_url, cached_requests)
    original_translations = {}
    original_translation_urls = {}
    default_translations = {}
    default_translation_url = None
    default_metadata = {}

    if len(locales) == 0:
        translatable = False
    else:
        translatable = True
        default_locale = None
        for locale in locales:
            lang = locale.attrib.get('lang')
            messages_url = locale.attrib.get('messages')
            if lang and messages_url and lang.lower() != 'all':
                if len(lang) == 2:
                    lang = u'%s_ALL' % lang
                try:
                    absolute_url, messages, metadata, locale_contents = _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests)
                except TranslatorError as e:
                    logging.warning(u"Could not load %s translation for app URL: %s Reason: %s" % (lang, app_url, e), exc_info = True)
                    continue
                else:
                    new_messages = {}
                    if messages:
                        for key, value in messages.iteritems():
                            new_messages[key] = value['text']
                    original_translations[lang] = new_messages
                    original_translation_urls[lang] = absolute_url

            if (lang is None or lang.lower() == 'all') and messages_url:
                # Process this later. This way we can force we get the results for the default translation
                default_locale = locale

        if default_locale is not None:
            messages_url = default_locale.attrib.get('messages')
            absolute_url, messages, metadata, locale_contents = _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests)
            default_translations = messages
            default_translation_url = absolute_url
            default_metadata = metadata

            # No English? Default is always English!
            if 'en_ALL' not in original_translations:
                lang = 'en_ALL'
                new_messages = {}
                if messages:
                    for key, value in messages.iteritems():
                        new_messages[key] = value['text']

                original_translations[lang] = new_messages
                original_translation_urls[lang] = absolute_url

    adaptable = ' data-configuration ' in body and ' data-configuration-definition ' in body

    metadata = {
        'translatable' : translatable,
        'adaptable' : adaptable,
        'original_translations' : original_translations,
        'original_translation_urls' : original_translation_urls,
        'default_translations' : default_translations,
        'default_translation_url' : default_translation_url,
        'default_metadata' : default_metadata,
    }
    
    serialized = json.dumps(metadata)
    metadata['hash'] = unicode(zlib.crc32(serialized))
    return metadata

def extract_messages_from_translation(messages_absolute_url, xml_contents):
    contents = fromstring(xml_contents)
    messages = {}
    attribs = dict(contents.attrib)
    if 'namespace' in contents.attrib:
        default_namespace = contents.attrib['namespace']
    else:
        default_namespace = None

    if 'mails' in contents.attrib:
        mails = [ mail.strip() for mail in contents.attrib['mails'].split(',') ]
    else:
        mails = []

    automatic = contents.attrib.get('automatic', 'true').lower() == 'true'

    for pos, xml_msg in enumerate(contents.findall('msg')):
        if 'name' not in xml_msg.attrib:
            raise TranslatorError("Invalid translation file: no name in msg tag")

        name = xml_msg.attrib['name']

        if 'category' in xml_msg.attrib:
            category = xml_msg.attrib['category']
        else:
            category = None

        if 'format' in xml_msg.attrib:
            format = xml_msg.attrib['format']
        else:
            format = "plain"

        if 'namespace' in xml_msg.attrib:
            namespace = xml_msg.attrib['namespace']
        else:
            namespace = default_namespace

        # if not category and namespace:
        #     category = namespace

        same_tool = True
        if 'toolId' in xml_msg.attrib:
            tool_id = xml_msg.attrib['toolId']
            if tool_id:
                basename = messages_absolute_url.rsplit('/', 1)[1]
                if not basename.startswith(tool_id):
                    same_tool = False
                hostname = urlparse.urlparse(messages_absolute_url).netloc
                # We generate the namespace based on the hostname. But localhost:5000 and composer.golabz.eu has a special hostname
                if messages_absolute_url.startswith(('http://localhost:5000/twente_commons/', 'http://composer.golabz.eu/twente_commons/')):
                    hostname = 'go-lab.gw.utwente.nl'
                namespace = "{0}::{1}".format(hostname, tool_id)
        else:
            tool_id = None

        # Some people use things like <msg name='foo'>Press <i class=''></i> to ...</msg>
        # This is invalid XML, but we want to support it too. So:
        try:
            # Get whatever is between the <msg name='foo'> and </msg>:
            raw_msg_message = ET.tostring(xml_msg).split(">", 1)[1].rsplit("<", 1)[0]
        except IndexError: 
            # If this ever happens, forget about it
            raw_msg_message = ""
        
        if '<' in raw_msg_message or '>' in raw_msg_message:   
            xml_text = raw_msg_message
        else:
            # However, we also want to support people using &lt;i class=''&gt;, so the 
            # code above is only used if < or > are present in the text. Otherwise we
            # trust the XML library
            xml_text = xml_msg.text or ""
        
        messages[name] = {
            'text' : xml_text,
            'category' : category,
            'namespace' : namespace,
            'position' : pos,
            'same_tool' : same_tool,
            'tool_id' : tool_id,
            'format': format,
        }
    metadata = {
        'mails' : mails,
        'automatic' : automatic,
        'attribs' : json.dumps(attribs),
    }
    return messages, metadata

def _raise_for_status(url, response):
    if response is None:
        raise requests.RequestException("URL: {0}: Expected response, returned None (probably in tests)".format(url))
    response.raise_for_status()

def _extract_locales(app_url, cached_requests):
    try:
        response = cached_requests.get(app_url, timeout = 30)
        _raise_for_status(app_url, response)
        xml_contents = get_text_from_response(response)
    except requests.RequestException as e:
        logging.warning(u"Could not load this app URL (%s): %s" % (app_url, e), exc_info = True)
        raise TranslatorError(u"Could not load this app URL: %s" % e)

    try:
        root = fromstring(xml_contents)
    except Exception as e:
        logging.warning(u"Invalid XML document (%s): %s" % (app_url, e), exc_info = True)
        print(u"Invalid XML document (%s): %s" % (app_url, e))
        raise TranslatorError("Invalid XML document: %s" % e)

    module_prefs = root.findall("ModulePrefs")
    if not module_prefs:
        raise TranslatorError("ModulePrefs not found in App URL")

    # TODO: here we should do more things:
    # - check if it's Smart Gateway or Embedder, if it mentions other URLs, check them
    # - check SSL
    # etc.

    locales = module_prefs[0].findall('Locale')
    return locales, xml_contents

def _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests):
    if messages_url.startswith(('http://', 'https://', '//')):
        absolute_translation_url = messages_url
    else:
        base_url = app_url.rsplit('/', 1)[0]
        absolute_translation_url = '/'.join((base_url, messages_url))

    try:
        translation_messages_response = cached_requests.get(absolute_translation_url, timeout = 30)
        _raise_for_status(absolute_translation_url, translation_messages_response)
        translation_messages_xml = get_text_from_response(translation_messages_response)
    except Exception as e:
        logging.warning("Could not reach locale URL: %s  Reason: %s" % (absolute_translation_url, e), exc_info = True)
        raise TranslatorError("Could not reach locale URL")
    
    # XXX TODO: Remove this list
    if absolute_translation_url.startswith('http://go-lab.gw.utwente.nl/production/'):
        translation_messages_xml = translation_messages_xml.replace("<messagebundle>", '<messagebundle mails="pablo.orduna@deusto.es">')

    try:
        messages, metadata = extract_messages_from_translation(absolute_translation_url, translation_messages_xml)
    except TranslatorError as e:
        logging.warning("Could not load XML contents from %s Reason: %s" % (absolute_translation_url, e), exc_info = True)
        raise TranslatorError("Could not load XML in %s" % absolute_translation_url)

    return absolute_translation_url, messages, metadata, translation_messages_xml


