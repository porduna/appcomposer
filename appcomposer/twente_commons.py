import json
import xml.etree.ElementTree as ET
from collections import OrderedDict

from flask import Blueprint, render_template, make_response
from appcomposer.translator.utils import get_cached_session, indent, get_text_from_response
from appcomposer.utils import report_error

twente_commons_blueprint = Blueprint('twente_commons', __name__)

def get_languages():
    requests = get_cached_session()
    languages = []
    for line in requests.get("http://go-lab.gw.utwente.nl/production/commons/languages/list.txt").text.splitlines():
        languages.append(line.split("_")[1])
    return languages

@twente_commons_blueprint.route('/')
@twente_commons_blueprint.route('/app.xml')
@report_error("Error on twente i18n")
def index():
    requests = get_cached_session()
    languages = get_languages()
    response = make_response(render_template('graasp_i18n.xml', languages = languages, title = "Twente commons"))
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
        'mails' : 'pablo.orduna@deusto.es',
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


@twente_commons_blueprint.route('/locales/common_<language>_ALL.xml')
@report_error("Error on twente i18n")
def locale(language):
    requests = get_cached_session()
    if language not in get_languages():
        return "Language not found", 404

    # xml_response = requests.get('http://go-lab.gw.utwente.nl/production/commons/commons_en_ALL.xml')
    xml_response = requests.get('http://go-lab.gw.utwente.nl/production/commons/languages/common_{0}_ALL.xml'.format(language))
    response = make_response(get_text_from_response(xml_response))
    response.content_type = 'application/xml'
    return response

