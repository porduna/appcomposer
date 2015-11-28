import time
import json
import codecs
import logging
import calendar
import datetime
import StringIO
import urlparse
from collections import OrderedDict
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
from appcomposer.translator.cdata import CDATA

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

def get_cached_session(caching = True):
    if not caching:
        return requests.Session()

    CACHE_DIR = 'web_cache'
    return CacheControl(requests.Session(),
                    cache=FileCache(CACHE_DIR), heuristic=LastModifiedNoDate(require_date=False))

def fromstring(xml_contents):
    try:
        return ET.fromstring(xml_contents.encode('utf8'))
    except Exception as e:
        logging.warning("Could not parse XML contents: %s" % e, exc_info = True)
        raise TranslatorError("Could not XML contents: %s" % e)

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

def raise_for_status(url, response):
    if response is None:
        raise requests.RequestException("URL: {0}: Expected response, returned None (probably in tests)".format(url))
    response.raise_for_status()

def _extract_locales(app_url, cached_requests):
    try:
        response = cached_requests.get(app_url, timeout = 30)
        raise_for_status(app_url, response)
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

    locales = module_prefs[0].findall('Locale')
    return locales, xml_contents

def _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests, only_if_new = False):
    if messages_url.startswith(('http://', 'https://', '//')):
        absolute_translation_url = messages_url
    else:
        base_url = app_url.rsplit('/', 1)[0]
        absolute_translation_url = '/'.join((base_url, messages_url))

    try:
        translation_messages_response = cached_requests.get(absolute_translation_url, timeout = 30)
        raise_for_status(absolute_translation_url, translation_messages_response)
        if only_if_new and hasattr(translation_messages_response, 'from_cache') and translation_messages_response.from_cache:
            return absolute_translation_url, None, {}
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

    return absolute_translation_url, messages, metadata

def extract_local_translations_url(app_url, force_local_cache = False):
    if force_local_cache:
        # Under some situations (e.g., updating a single message), it is better to have a cache
        # than contacting the foreign server. Only if requested, this method will try to check
        # in a local cache in the database.
        last_hour = datetime.datetime.utcnow() - datetime.timedelta(hours = 1)
        cached = db.session.query(TranslationFastCache.translation_url, TranslationFastCache.original_messages, TranslationFastCache.app_metadata).filter(TranslationFastCache.app_url == app_url, TranslationFastCache.datetime > last_hour).first()
        if cached is not None:
            translation_url, original_messages, metadata = cached
            if metadata is not None:
                original_messages_loaded = json.loads(original_messages)
                metadata_loaded = json.loads(metadata)
                return translation_url, original_messages_loaded, metadata_loaded

    cached_requests = get_cached_session()

    locales, _ = _extract_locales(app_url, cached_requests)

    locales_without_lang = [ locale for locale in locales if 'lang' not in locale.attrib or locale.attrib['lang'].lower() == 'all' ]
    if not locales_without_lang:
        raise TranslatorError("No default Locale found")

    relative_translation_url = locales_without_lang[0].attrib.get('messages')
    if not relative_translation_url:
        raise TranslatorError("Default Locale not provided message attribute")

    absolute_translation_url, messages, metadata = _retrieve_messages_from_relative_url(app_url, relative_translation_url, cached_requests)

    try:
        db.session.query(TranslationFastCache).filter_by(app_url = app_url).delete()
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.warning("Error deleting existing caches: %s" % e, exc_info = True)

    cache = TranslationFastCache(app_url = app_url, translation_url =  absolute_translation_url, original_messages = json.dumps(messages), datetime = datetime.datetime.utcnow(), app_metadata = json.dumps(metadata))
    db.session.add(cache)
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.warning("Could not add element to cache: %s" % e, exc_info = True)
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
                only_if_new = not force_reload
                try:
                    absolute_url, messages, metadata = _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests, only_if_new = only_if_new)
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
            absolute_url, messages, metadata = _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests, only_if_new = False)
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

    return {
        'translatable' : translatable,
        'adaptable' : adaptable,
        'original_translations' : original_translations,
        'original_translation_urls' : original_translation_urls,
        'default_translations' : default_translations,
        'default_translation_url' : default_translation_url,
        'default_metadata' : default_metadata,
    }

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
                hostname = urlparse.urlparse(messages_absolute_url)
                namespace = "{0}::{1}".format(hostname.netloc, tool_id)
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

NO_CATEGORY = 'no-category'
NO_TOOL = 'no-tool'

def _get_sorted_messages(db_bundle, category, tool_id):
    if category is None:
        active_messages = [ am for am in db_bundle.active_messages ]
    elif category == NO_CATEGORY:
        active_messages = [ am for am in db_bundle.active_messages if am.category == None ]
    else:
        active_messages = [ am for am in db_bundle.active_messages if am.category == category ]

    if tool_id == NO_TOOL:
        active_messages = [ am for am in active_messages if am.tool_id == None ]
    elif tool_id is None:
        pass
    else:
        active_messages = [ am for am in active_messages if am.tool_id == tool_id ]

    active_messages.sort(lambda am1, am2 : cmp(am1.position, am2.position))
    return active_messages

def bundle_to_xml(db_bundle, category = None, tool_id = None):
    xml_bundle = ET.Element("messagebundle", attrib = OrderedDict())
    own_tool_id = None
    requires = set()
    for message in _get_sorted_messages(db_bundle, category, tool_id):
        if message.same_tool:
            own_tool_id = message.tool_id
        if message.tool_id and not message.same_tool:
            requires.add(message.tool_id)

        attrib = OrderedDict()
        if message.tool_id:
            attrib['toolId'] = message.tool_id
        elif message.namespace:
            attrib['namespace'] = message.namespace
        attrib['name'] = message.key
        if message.category:
            attrib['category'] = message.category
        if message.fmt and message.fmt != 'plain':
            attrib['format'] = message.fmt
        
        xml_msg = ET.SubElement(xml_bundle, 'msg', attrib = attrib)
        if '<' in message.value or '>' in message.value or '&' in message.value:
            xml_msg.append(CDATA(message.value))
        else:            
            xml_msg.text = message.value

    if db_bundle.translation_url:
        root_attribs = db_bundle.translation_url.attribs
    else:
        root_attribs = ''

    if root_attribs:
        try:
            attribs = json.loads(root_attribs)
        except:
            traceback.print_exc()
            attribs = {}
        xml_bundle.attrib.update(attribs)

    indent(xml_bundle)
    xml_string = ET.tostring(xml_bundle, encoding = 'UTF-8')
    return xml_string

def bundle_to_properties(db_bundle, category = None, tool_id = None):
    properties_file = StringIO.StringIO()
    for message in _get_sorted_messages(db_bundle, category, tool_id):
        properties_file.write(message.key)
        properties_file.write(" = ")
        properties_file.write(message.value.strip())
        properties_file.write("\n")
    return properties_file.getvalue()

def bundle_to_json(db_bundle, category = None, tool_id = None):
    result = {}
    for message in _get_sorted_messages(db_bundle, category, tool_id):
        value = {
            'value' : message.value
        }
        if message.category:
            value['category'] = message.category
        if message.namespace:
            value['namespace'] = message.namespace
        result[message.key] = value
    return json.dumps(result, indent = 4)

def bundle_to_graasp_json(db_bundle, category = None, tool_id = None):
    # 
    result = OrderedDict()
    for message in _get_sorted_messages(db_bundle, category, tool_id):
        sub_keys = message.key.split('::')
        key = sub_keys[-1]
        parents = sub_keys[:-1]
        current = result
        for parent in parents:
            if parent in current:
                current = current[parent]
            else:
                current[parent] = OrderedDict()
                current = current[parent]
        current[key] = message.value
    return json.dumps(result, indent = 4)

def bundle_to_jquery_i18n(db_bundle, category = None, tool_id = None):
    result = OrderedDict()
    active_messages = _get_sorted_messages(db_bundle, category, tool_id)

    result["@metadata"] = {
        "locale" : db_bundle.language,
        "message-documentation": ""
    }
    datetimes = [ am.datetime for am in active_messages ]
    if datetimes:
        result["@metadata"]["last-updated"] = max(datetimes).strftime("%Y-%m-%d")
    
    # 
    # We don't want to avoid being anonymous, but this one should be quite easy
    # users = set([ am.history.user.display_name for am in active_messages ])
    # if users:
    #     result["@metadata"]["authors"] = list(users)

    for message in active_messages:
        result[message.key] = message.value
    return json.dumps(result, indent = 4)

def messages_to_xml(messages):
    xml_bundle = ET.Element("messagebundle")
    keys = sorted(messages.keys())
    for key in keys:
        value = messages[key]
        xml_msg = ET.SubElement(xml_bundle, 'msg')
        xml_msg.attrib['name'] = key
        xml_msg.text = value
    indent(xml_bundle)
    xml_string = ET.tostring(xml_bundle, encoding = 'UTF-8')
    return xml_string


def url_to_filename(url):
    return requests.utils.quote(url, '').replace('%', '_')
