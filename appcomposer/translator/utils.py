import time
import json
import logging
import calendar
import StringIO
import traceback
from collections import OrderedDict
import xml.etree.ElementTree as ET
from email.utils import parsedate, parsedate_tz

import requests
import requests.packages.urllib3 as urllib3
urllib3.disable_warnings()
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
from cachecontrol.heuristics import LastModified, TIME_FMT

from appcomposer.exceptions import TranslatorError
from appcomposer.cdata import CDATA

class _LastModifiedNoDate(LastModified):
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
        # So, by default, if it has a last-modified, don't check in the next 5 minutes. (not 1 day as it was previously defined)
        MAX_TIME = 300 # seconds
        freshness_lifetime = max(0, min(delta * self.error_margin, MAX_TIME)) # max so as to avoid negative numbers
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
                    cache=FileCache(CACHE_DIR), heuristic=_LastModifiedNoDate(require_date=False))

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
        # Try to preserve the order
        for field in 'toolId', 'mails', 'requires':
            if field in attribs:
                xml_bundle.attrib[field] = attribs.pop(field)
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
    return json.dumps(result, indent = 2, separators=(',', ': ')) + '\n'

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
