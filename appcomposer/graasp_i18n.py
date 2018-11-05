import json
import xml.etree.ElementTree as ET
from collections import OrderedDict

from flask import Blueprint, render_template, make_response, current_app
from appcomposer.translator.utils import get_cached_session, indent
from appcomposer.utils import report_error

graasp_i18n_blueprint = Blueprint('graasp_i18n', __name__)

SPACE_URL = 'http://graasp.eu/spaces/560410b2f0e1b09f6c8116da'

def get_languages():
    return ['en']

class TimeoutError(Exception):
    pass

def get_contents(lang):
    if lang == 'en':
        resource_id = '560410f1f0e1b09f6c8117ec'
        requests = get_cached_session()
        request_url = "http://graasp.eu/resources/{0}/raw".format(resource_id)
        try:
            r = requests.get(request_url, timeout=(10,10))
            r.raise_for_status()
        except Exception:
            raise TimeoutError("Timeout")

        try:
            return json.JSONDecoder(object_pairs_hook=OrderedDict).decode(r.text)
        except ValueError as ve:
            if len(r.text) == 0:
                raise ValueError("{}: {} returned empty result!".format(ve, request_url))
                
            if len(r.text) >= 20:
                response = '{!r}...'.format(r.text[:20])
            else:
                response = r.text
            raise ValueError("{}: {}: {!r}".format(ve, request_url, response))
    else:
        return None

@graasp_i18n_blueprint.route('/')
@graasp_i18n_blueprint.route('/app.xml')
@report_error("Error on graasp i18n at the App Composer", additional_recipients = [])
def index():
    languages = get_languages()
    response = make_response(render_template('graasp_i18n.xml', languages = languages, title = "Graasp"))
    response.content_type = 'application/xml'
    return response

def _parse_contents(contents, dictionary, parent_key = ''):
    for key, value in contents.items():
        if parent_key:
            cur_key = '%s::%s' % (parent_key, key)
        else:
            cur_key = key

        if isinstance(value, dict):
            _parse_contents(value, dictionary, cur_key)
        else:
            dictionary[cur_key] = value

def messages_to_xml(messages):
    xml_bundle = ET.Element("messagebundle")
    xml_bundle.attrib.update({
        'mails' : 'pablo.orduna@deusto.es,{}'.format(','.join(current_app.config.get('GRAASP_ADMINS', []))),
        'automatic' : 'false'
    })
    for key in messages.keys():
        value = messages[key]
        xml_msg = ET.SubElement(xml_bundle, 'msg')
        xml_msg.attrib['name'] = key
        xml_msg.text = value
    indent(xml_bundle)
    xml_string = ET.tostring(xml_bundle, encoding = 'UTF-8')
    return xml_string


@graasp_i18n_blueprint.route('/locales/graasp_<language>_ALL.xml')
@report_error("Error on graasp i18n", additional_recipients = [])
def locale(language):
    try:
        contents = get_contents(language)
    except TimeoutError:
        return "Error retrieving external resource", 502

    if contents is None:
        return "Language not found", 404
    i18n_contents = OrderedDict()
    _parse_contents(contents, i18n_contents)
    xml_response = messages_to_xml(i18n_contents)
    response = make_response(xml_response)
    response.content_type = 'application/xml'
    return response

