import re
import json
import urllib2
import traceback
from xml.dom import minidom

from flask import render_template, request, flash, url_for

from appcomposer.utils import make_url_absolute, inject_absolute_urls, get_json, inject_original_url_in_xmldoc, inject_absolute_locales_in_xmldoc
from appcomposer.composers.adapt import create_adaptor

adaptor = create_adaptor('JavaScript configuration', 
                initial = {'url' : None, 'configuration' : None, 'configuration_name' : None})

SHINDIG_SERVER = 'http://shindig.epfl.ch'
def shindig_url(relative_url):
    return '%s%s' % (SHINDIG_SERVER, relative_url)


CONFIG_DEFINITION_REGEX = re.compile(r"""(<\s*script[^<]*\sdata-configuration-definition(?:>|\s[^>]*>))""")
SRC_REGEX = re.compile(r"""src\s*=\s*["']?([^"']+)["']?""")

def find_definition_script(contents, url):
    data_config_definition_scripts = CONFIG_DEFINITION_REGEX.findall(contents)
    if len(data_config_definition_scripts) > 1:
        flash("Too many scripts with data-configuration-definition found. This may happen if you have commented one. There can be a single one.")
    elif len(data_config_definition_scripts) < 1:
        flash("No script with data-configuration-definition found. Is the app adapted for the Go-Lab JavaScript configuration tools?")
    else:
        src_attributes = SRC_REGEX.findall(data_config_definition_scripts[0])
        if len(src_attributes) > 1:
            flash("In the data-configuration-definition tag, there must be a single src attribute")
        elif len(src_attributes) < 1:
            flash("In the data-configuration-definition tag, there must be at least an src attribute. None found")
        else:
            src_attribute = src_attributes[0]
            return make_url_absolute(src_attribute, url)

DEFAULT_CONFIG_REGEX = re.compile(r"""(<\s*script[^<]*\sdata-configuration(?:>|\s[^>]*>))""")

def replace_default_configuration_script(contents, new_url):
    return DEFAULT_CONFIG_REGEX.sub('<script data-configuration type="text/javascript" src="%s">' % new_url, contents)

@adaptor.edit_route
def edit(app_id):
    # Load data from the database for this application
    data = adaptor.load_data(app_id)
        
    contents = None
    if request.method == 'POST':
        value = request.form['url']
        if value != data['url']:
            try:
                contents = urllib2.urlopen(value).read()
            except:
                flash("Could not download the provided URL")
            else:
                try:
                    minidom.parseString(contents)
                except:
                    flash("The provided URL is not a valid XML!")
                else:
                    # Reset the configuration
                    data['url'] = value
                    data['configuration'] = None
                    data['configuration_name'] = None
                    adaptor.save_data(app_id, data)

    url = data['url']
    definition_script = None

    if url and url.startswith(('http://', 'https://')):
        if not contents:
            try:
                contents = urllib2.urlopen(url).read()
            except:
                flash("Could not download the provided URL")
        if contents:
            definition_script = find_definition_script(contents, url)

    external_url = url_for('.app_xml', app_id = app_id, _external = True)
    preview_url = shindig_url("/gadgets/ifr?nocache=1&url=%s" % external_url)
    configuration_name = data['configuration_name']
    configuration = json.dumps(data['configuration'], indent = 4)

    return render_template("jsconfig/edit.html",  
                                url = url or '',
                                definition_script = definition_script,
                                app_id = app_id,
                                preview_url = preview_url,
                                configuration_name = configuration_name,
                                configuration = configuration)

@adaptor.route('/save/<app_id>/', methods = ['GET', 'POST'])
def save_json_config(app_id):
    # TODO: CSRF
    if request.method == 'POST':
        json_contents = get_json()
        if json_contents:
            print json_contents
            data = adaptor.load_data(app_id)
            data['configuration_name'] = json_contents.get('appName', 'appName not found')
            data['configuration'] = json_contents.get('config', {})
            adaptor.save_data(app_id, data)
        else:
            return 'error: malformed json content'

    return 'ok'

@adaptor.route('/export/<app_id>/app.xml')
def app_xml(app_id):
    try:
        data = adaptor.load_data(app_id)
        url = data['url']
        contents = urllib2.urlopen(url).read()
        contents = replace_default_configuration_script(contents, url_for('.configuration', app_id = app_id, _external = True))
        contents = inject_absolute_urls(contents, url)
        xmldoc = minidom.parseString(contents)
        inject_original_url_in_xmldoc(xmldoc, url)
        inject_absolute_locales_in_xmldoc(xmldoc, url)
        contents = xmldoc.toprettyxml()
    except Exception as e:
        traceback.print_exc()
        # TODO: some bootstrap magic
        return "Could not convert the application. %s" % str(e)
    else:
        return contents

@adaptor.route('/export/<app_id>/configuration.js')
def configuration(app_id):
    data = adaptor.load_data(app_id)
    name = data.get('configuration_name', 'missing-name')
    configuration = data.get('configuration', {})
    configuration_json = json.dumps(configuration, indent = 4)
    return render_template("jsconfig/configuration.js", name = name, configuration = configuration_json)

