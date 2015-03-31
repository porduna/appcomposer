import requests
import xml.etree.ElementTree as ET

def extract_local_translations_url(app_url):
    try:
        xml_contents = requests.get(app_url).text
    except:
        raise Exception("Could not load this app URL")

    try:
        root = ET.fromstring(xml_contents)
    except:
        raise Exception("Invalid XML document")

    module_prefs = root.findall("ModulePrefs")
    if not module_prefs:
        raise Exception("ModulePrefs not found in App URL")

    locales = module_prefs[0].findall('Locale')
    locales_without_lang = [ locale for locale in locales if 'lang' not in locale.attrib ]
    if not locales_without_lang:
        raise Exception("No default Locale found")

    relative_translation_url = locales_without_lang[0].attrib.get('messages')
    if not relative_translation_url:
        raise Exception("Default Locale not provided message attribute")

    if relative_translation_url.startswith(('http://', 'https://', '//')):
        absolute_translation_url = relative_translation_url
    else:
        base_url = app_url.rsplit('/', 1)[0]
        absolute_translation_url = '/'.join((base_url, relative_translation_url))

    try:
        translation_messages_xml = requests.get(absolute_translation_url).text
    except:
        raise Exception("Could not reach default locale URL")

    messages = extract_messages_from_translation(translation_messages_xml)
    return absolute_translation_url, messages

def extract_messages_from_translation(xml_contents):
    contents = ET.fromstring(xml_contents)
    messages = {}
    for xml_msg in contents.findall('msg'):
        if 'name' not in xml_msg.attrib:
            raise Exception("Invalid translation file: no name in msg tag")
        messages[xml_msg.attrib['name']] = xml_msg.text
    return messages
