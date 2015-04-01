import traceback
import requests
import xml.etree.ElementTree as ET
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

DEBUG = True

def get_cached_session():
    CACHE_DIR = 'web_cache'
    return CacheControl(requests.Session(),
                    cache=FileCache(CACHE_DIR))

def _extract_locales(app_url, cached_requests):
    try:
        xml_contents = cached_requests.get(app_url).text
    except:
        traceback.print_exc()
        raise Exception("Could not load this app URL")

    try:
        root = ET.fromstring(xml_contents.encode('utf8'))
    except:
        traceback.print_exc()
        raise Exception("Invalid XML document")

    module_prefs = root.findall("ModulePrefs")
    if not module_prefs:
        raise Exception("ModulePrefs not found in App URL")

    locales = module_prefs[0].findall('Locale')
    return locales, xml_contents

def _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests, only_if_new = False):
    if relative_translation_url.startswith(('http://', 'https://', '//')):
        absolute_translation_url = relative_translation_url
    else:
        base_url = app_url.rsplit('/', 1)[0]
        absolute_translation_url = '/'.join((base_url, relative_translation_url))

    try:
        translation_messages_response = cached_requests.get(absolute_translation_url)
        if only_if_new and translation_messages_response.from_cache:
            return None
        translation_messages_xml = translation_messages_response.text
    except:
        raise Exception("Could not reach default locale URL")

    messages = extract_messages_from_translation(translation_messages_xml)
    return messages

def extract_local_translations_url(app_url):
    cached_requests = get_cached_session()

    locales, _ = _extract_locales(app_url, cached_requests)

    locales_without_lang = [ locale for locale in locales if 'lang' not in locale.attrib ]
    if not locales_without_lang:
        raise Exception("No default Locale found")

    relative_translation_url = locales_without_lang[0].attrib.get('messages')
    if not relative_translation_url:
        raise Exception("Default Locale not provided message attribute")

    messages = _retrieve_messages_from_relative_url(app_url, relative_translation_url, cached_requests)
    return absolute_translation_url, messages

def extract_metadata_information(app_url, cached_requests = None):
    if cached_requests is None:
        cached_requests = get_cached_session()

    locales, body = _extract_locales(app_url, cached_requests)
    original_translations = []
    if len(locales) == 0:
        translatable = False
    else:
        translatable = True
        for locale in locales:
            lang = locale.attrib.get('lang')
            messages_url = locale.attrib.get('messages')
            if lang and messages_url:
                if len(lang) == 2:
                    lang = u'%s_ALL' % lang
                messages = _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests, only_if_new = True)
                if messages is None:
                    # TODO: skip?
                    pass
                original_translations[lang] = messages

    adaptable = ' data-configuration ' in body and ' data-configuration-definition ' in body

    return {
        'translatable' : translatable,
        'adaptable' : adaptable,
        'original_translations' : original_translations,
    }

def extract_messages_from_translation(xml_contents):
    contents = ET.fromstring(xml_contents.encode('utf8'))
    messages = {}
    for xml_msg in contents.findall('msg'):
        if 'name' not in xml_msg.attrib:
            raise Exception("Invalid translation file: no name in msg tag")
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
