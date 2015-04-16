import time
import json
import codecs
import logging
import calendar
import datetime
import xml.etree.ElementTree as ET
from email.utils import formatdate, parsedate, parsedate_tz

from sqlalchemy.exc import SQLAlchemyError
import requests
import requests.packages.urllib3 as urllib3
urllib3.disable_warnings()
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
from cachecontrol.heuristics import LastModified, TIME_FMT

from appcomposer import db
from appcomposer.models import TranslationFastCache
from appcomposer.translator.exc import TranslatorError

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

def get_text_from_response(response):
    """requests Response's text property automatically uses the default encoding to convert it to unicode
    However, sometimes it falls back to ISO-8859-1, which is not appropriate. This method checks whether it
    could be interpreted as UTF-8. If it is, it uses it. Otherwise, it uses whatever was defined. 
    """
    if response.encoding is None:
        response.encoding = 'utf8'
    elif response.encoding == 'ISO-8859-1':
        try:
            response.content.decode('utf8')
        except UnicodeDecodeError:
            pass
        else:
            response.encoding = 'utf8'
    return response.text

def _extract_locales(app_url, cached_requests):
    try:
        response = cached_requests.get(app_url)
        response.raise_for_status()
        xml_contents = get_text_from_response(response)
    except requests.RequestException as e:
        logging.warning(u"Could not load this app URL: %s" % e, exc_info = True)
        raise TranslatorError(u"Could not load this app URL: %s" % e)

    try:
        root = fromstring(xml_contents)
    except Exception as e:
        logging.warning(u"Invalid XML document: %s" % e, exc_info = True)
        raise TranslatorError("Invalid XML document: %s" % e)

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
        translation_messages_response.raise_for_status()
        if only_if_new and translation_messages_response.from_cache:
            return absolute_translation_url, None
        translation_messages_xml = get_text_from_response(translation_messages_response)
    except Exception as e:
        logging.warning("Could not reach default locale URL: %s" % e, exc_info = True)
        raise TranslatorError("Could not reach default locale URL")

    messages = extract_messages_from_translation(translation_messages_xml)
    return absolute_translation_url, messages

def extract_local_translations_url(app_url, force_local_cache = False):
    if force_local_cache:
        # Under some situations (e.g., updating a single message), it is better to have a cache
        # than contacting the foreign server. Only if requested, this method will try to check
        # in a local cache in the database.
        last_hour = datetime.datetime.now() - datetime.timedelta(hours = 1)
        cached = db.session.query(TranslationFastCache.translation_url, TranslationFastCache.original_messages).filter(TranslationFastCache.app_url == app_url, TranslationFastCache.datetime > last_hour).first()
        if cached is not None:
            translation_url, original_messages = cached
            return translation_url, json.loads(original_messages)

    cached_requests = get_cached_session()

    locales, _ = _extract_locales(app_url, cached_requests)

    locales_without_lang = [ locale for locale in locales if 'lang' not in locale.attrib or locale.attrib['lang'].lower() == 'all' ]
    if not locales_without_lang:
        raise TranslatorError("No default Locale found")

    relative_translation_url = locales_without_lang[0].attrib.get('messages')
    if not relative_translation_url:
        raise TranslatorError("Default Locale not provided message attribute")

    absolute_translation_url, messages = _retrieve_messages_from_relative_url(app_url, relative_translation_url, cached_requests)

    db.session.query(TranslationFastCache).filter_by(app_url = app_url).delete()
    cache = TranslationFastCache(app_url = app_url, translation_url =  absolute_translation_url, original_messages = json.dumps(messages), datetime = datetime.datetime.now())
    db.session.add(cache)
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        logging.warning("Could not add element to cache: %s" % e, exc_info = True)
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
            if lang and messages_url and lang.lower() != 'all':
                if len(lang) == 2:
                    lang = u'%s_ALL' % lang
                only_if_new = not force_reload
                absolute_url, messages = _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests, only_if_new = only_if_new)
                original_translations[lang] = messages
                original_translation_urls[lang] = absolute_url

            if (lang is None or lang.lower() == 'all') and messages_url:
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

def messages_to_xml(messages):
    xml_bundle = ET.Element("messagebundle")
    for key, value in messages.iteritems():
        xml_msg = ET.SubElement(xml_bundle, 'msg')
        xml_msg.attrib['name'] = key
        xml_msg.text = value
    indent(xml_bundle)
    xml_string = ET.tostring(xml_bundle, encoding = 'utf8')
    return xml_string


def url_to_filename(url):
    return requests.utils.quote(url, '').replace('%', '_')