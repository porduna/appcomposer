import xml.etree.ElementTree as ET

from flask import Blueprint, render_template, make_response
from appcomposer.translator.utils import get_cached_session, indent

graasp_i18n_blueprint = Blueprint('graasp_i18n', __name__)

SPACE_URL = 'http://graasp.eu/spaces/560410b2f0e1b09f6c8116da'

def get_languages():
    requests = get_cached_session()
    languages = []
    for item in requests.get(SPACE_URL, headers = {'Accept' : 'application/json' }).json()['items']:
        if item['name'].endswith('.json'):
            lang_name = item['name'].rsplit('.json', 1)[0]
            if len(lang_name) == 2:
                languages.append(lang_name)
    return languages

def get_contents(lang):
    requests = get_cached_session()
    languages = []
    for item in requests.get(SPACE_URL, headers = {'Accept' : 'application/json' }).json()['items']:
        if item['name'] == '%s.json' % lang:
            resource_id = item['_id']
            return requests.get("http://graasp.eu/resources/{0}/raw".format(resource_id)).json()

    return None

@graasp_i18n_blueprint.route('/')
@graasp_i18n_blueprint.route('/app.xml')
def index():
    requests = get_cached_session()
    languages = get_languages()
    response = make_response(render_template('graasp_i18n.xml', languages = languages))
    response.content_type = 'application/xml'
    return response

def _parse_contents(contents, dictionary, parent_key = ''):
    for key, value in contents.items():
        if isinstance(value, dict):
            if parent_key:
                cur_key = '%s::%s' % (parent_key, key)
            else:
                cur_key = key

            _parse_contents(value, dictionary, cur_key)
        else:
            if parent_key:
                cur_key = '%s::%s' % (parent_key, key)
            else:
                cur_key = key

            dictionary[cur_key] = value

def messages_to_xml(messages):
    xml_bundle = ET.Element("messagebundle")
    xml_bundle.attrib.update({
        'mails' : 'pablo.orduna@deusto.es,alex.wild@epfl.ch',
        'automatic' : 'false'
    })
    keys = sorted(messages.keys())
    for key in keys:
        value = messages[key]
        xml_msg = ET.SubElement(xml_bundle, 'msg')
        xml_msg.attrib['name'] = key
        xml_msg.text = value
    indent(xml_bundle)
    xml_string = ET.tostring(xml_bundle, encoding = 'UTF-8')
    return xml_string


@graasp_i18n_blueprint.route('/locales/graasp_<language>_ALL.xml')
def locale(language):
    requests = get_cached_session()
    contents = get_contents(language)
    if contents is None:
        return "Language not found", 404
    i18n_contents = {}
    _parse_contents(contents, i18n_contents)
    xml_response = messages_to_xml(i18n_contents)
    response = make_response(xml_response)
    response.content_type = 'application/xml'
    return response

