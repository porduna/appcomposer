import json
import xml.etree.ElementTree as ET
from collections import OrderedDict

from flask import Blueprint, render_template, make_response
from appcomposer.translator.utils import get_cached_session, indent
from appcomposer.utils import report_error

graasp_i18n_blueprint = Blueprint('graasp_i18n', __name__)

SPACE_URL = 'http://graasp.eu/spaces/560410b2f0e1b09f6c8116da'

def get_languages():
    return ['en']
#     requests = get_cached_session()
#     languages = []
#     for item in requests.get(SPACE_URL, headers = {'Accept' : 'application/json' }).json()['items']:
#         if item['name'].endswith('.json'):
#             lang_name = item['name'].rsplit('.json', 1)[0]
#             if len(lang_name) == 2:
#                 languages.append(lang_name)
#     return languages

def get_contents(lang):
    if lang == 'en':
        resource_id = '560410f1f0e1b09f6c8117ec'
        requests = get_cached_session()
        request_url = "http://graasp.eu/resources/{0}/raw".format(resource_id)
        r = requests.get(request_url)
        r.raise_for_status()
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
#     requests = get_cached_session()
#     languages = []
#     for item in requests.get(SPACE_URL, headers = {'Accept' : 'application/json' }).json()['items']:
#         if item['name'] == '%s.json' % lang:
#             resource_id = item['_id']
#             r = requests.get("http://graasp.eu/resources/{0}/raw".format(resource_id))
#             r.raise_for_status()
#             return json.JSONDecoder(object_pairs_hook=OrderedDict).decode(r.text)
# 
#     return None

@graasp_i18n_blueprint.route('/')
@graasp_i18n_blueprint.route('/app.xml')
@report_error("Error on graasp i18n at the App Composer", additional_recipients = ['alex.wild@epfl.ch'])
def index():
    requests = get_cached_session()
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
        'mails' : 'pablo.orduna@deusto.es,graasp@groupes.epfl.ch',
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
@report_error("Error on graasp i18n", additional_recipients = ['alex.wild@epfl.ch'])
def locale(language):
    requests = get_cached_session()
    contents = get_contents(language)
    if contents is None:
        return "Language not found", 404
    i18n_contents = OrderedDict()
    _parse_contents(contents, i18n_contents)
    xml_response = messages_to_xml(i18n_contents)
    response = make_response(xml_response)
    response.content_type = 'application/xml'
    return response

