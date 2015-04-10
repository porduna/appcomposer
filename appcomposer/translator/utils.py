import codecs
import traceback
import requests
import xml.etree.ElementTree as ET
import requests.packages.urllib3 as urllib3
urllib3.disable_warnings()
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
from cachecontrol.heuristics import LastModified, TIME_FMT
from appcomposer.translator.exc import TranslatorError

import calendar
import time
from email.utils import formatdate, parsedate, parsedate_tz

DEBUG = True

class LastModifiedNoDate(LastModified):
    """ This takes the original LastModified implementation of 
    cachecontrol, but defaults the date in case it is not provided.
    """
    def __init__(self, require_date = True, error_margin = None):
        if error_margin is None:
            if require_date:
                self.error_margin = 0.1
            else:
                self.error_margin = 0.2
        else:
            self.error_margin = error_margin
        self.require_date = require_date

    def update_headers(self, resp):
        headers = resp.headers
        if 'expires' in headers:
            return {}

        if 'cache-control' in headers and headers['cache-control'] != 'public':
            return {}

        if resp.status not in self.cacheable_by_default_statuses:
            return {}

        if 'last-modified' not in headers:
            return {}

        parsed_date = parsedate_tz(headers.get('date'))
        if self.require_date and parsed_date is None:
            return {}
        
        if parsed_date is None:
            date = time.time()
            faked_date = True
        else:
            date = calendar.timegm(parsed_date)
            faked_date = False

        last_modified = parsedate(headers['last-modified'])
        if last_modified is None:
            return {}

        now = time.time()
        current_age = max(0, now - date)
        delta = date - calendar.timegm(last_modified)
        freshness_lifetime = max(0, min(delta * self.error_margin, 24 * 3600))
        if freshness_lifetime <= current_age:
            return {}

        expires = date + freshness_lifetime
        new_headers = {'expires': time.strftime(TIME_FMT, time.gmtime(expires))}
        if faked_date:
            new_headers['date'] = time.strftime(TIME_FMT, time.gmtime(date))
        return new_headers

    def warning(self, resp):
        return None

def get_cached_session():
    CACHE_DIR = 'web_cache'
    return CacheControl(requests.Session(),
                    cache=FileCache(CACHE_DIR), heuristic=LastModifiedNoDate(require_date=False))

def fromstring(xml_contents):
    return ET.fromstring(xml_contents.encode('utf8'))

def _extract_locales(app_url, cached_requests):
    try:
        response = cached_requests.get(app_url)
        if response.encoding is None:
            response.encoding = 'utf8'
        xml_contents = response.text
    except Exception:
        traceback.print_exc()
        raise TranslatorError("Could not load this app URL")

    try:
        root = fromstring(xml_contents)
    except Exception:
        traceback.print_exc()
        raise TranslatorError("Invalid XML document")

    module_prefs = root.findall("ModulePrefs")
    if not module_prefs:
        raise TranslatorError("ModulePrefs not found in App URL")

    locales = module_prefs[0].findall('Locale')
    return locales, xml_contents

def _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests, only_if_new = False):
    if messages_url.startswith(('http://', 'https://', '//')):
        absolute_translation_url = messages_url
    else:
        base_url = app_url.rsplit('/', 1)[0]
        absolute_translation_url = '/'.join((base_url, messages_url))

    try:
        translation_messages_response = cached_requests.get(absolute_translation_url)
        if only_if_new and translation_messages_response.from_cache:
            return absolute_translation_url, None
        if translation_messages_response.encoding is None:
            translation_messages_response.encoding = 'utf8'
        translation_messages_xml = translation_messages_response.text
    except Exception:
        raise TranslatorError("Could not reach default locale URL")

    messages = extract_messages_from_translation(translation_messages_xml)
    return absolute_translation_url, messages

def extract_local_translations_url(app_url):
    cached_requests = get_cached_session()

    locales, _ = _extract_locales(app_url, cached_requests)

    locales_without_lang = [ locale for locale in locales if 'lang' not in locale.attrib ]
    if not locales_without_lang:
        raise TranslatorError("No default Locale found")

    relative_translation_url = locales_without_lang[0].attrib.get('messages')
    if not relative_translation_url:
        raise TranslatorError("Default Locale not provided message attribute")

    absolute_translation_url, messages = _retrieve_messages_from_relative_url(app_url, relative_translation_url, cached_requests)
    return absolute_translation_url, messages

def extract_metadata_information(app_url, cached_requests = None, force_reload = False):
    if cached_requests is None:
        cached_requests = get_cached_session()

    locales, body = _extract_locales(app_url, cached_requests)
    original_translations = {}
    original_translation_urls = {}
    default_translations = {}
    default_translation_url = None
    if len(locales) == 0:
        translatable = False
    else:
        translatable = True
        default_locale = None
        for locale in locales:
            lang = locale.attrib.get('lang')
            messages_url = locale.attrib.get('messages')
            if lang and messages_url:
                if len(lang) == 2:
                    lang = u'%s_ALL' % lang
                only_if_new = not force_reload
                absolute_url, messages = _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests, only_if_new = only_if_new)
                original_translations[lang] = messages
                original_translation_urls[lang] = absolute_url

            if lang is None and messages_url:
                # Process this later. This way we can force we get the results for the default translation
                default_locale = locale

        if default_locale is not None:
            messages_url = default_locale.attrib.get('messages')
            absolute_url, messages = _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests, only_if_new = False)
            default_translations = messages
            default_translation_url = absolute_url

    adaptable = ' data-configuration ' in body and ' data-configuration-definition ' in body

    return {
        'translatable' : translatable,
        'adaptable' : adaptable,
        'original_translations' : original_translations,
        'original_translation_urls' : original_translation_urls,
        'default_translations' : default_translations,
        'default_translation_url' : default_translation_url,
    }

def extract_messages_from_translation(xml_contents):
    contents = fromstring(xml_contents)
    messages = {}
    for xml_msg in contents.findall('msg'):
        if 'name' not in xml_msg.attrib:
            raise TranslatorError("Invalid translation file: no name in msg tag")
        messages[xml_msg.attrib['name']] = xml_msg.text
    return messages


def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def bundle_to_xml(db_bundle):
    xml_bundle = ET.Element("messagebundle")
    for message in db_bundle.active_messages:
        xml_msg = ET.SubElement(xml_bundle, 'msg')
        xml_msg.attrib['name'] = message.key
        xml_msg.text = message.value
    indent(xml_bundle)
    xml_string = ET.tostring(xml_bundle, encoding = 'utf8')
    return xml_string

def url_to_filename(url):
    return requests.utils.quote(url, '').replace('%', '_')
