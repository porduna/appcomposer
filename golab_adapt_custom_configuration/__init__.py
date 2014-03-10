import urllib2
import urlparse
import socket

from flask import render_template, request
from appcomposer.composers.adapt import create_adaptor

adaptor = create_adaptor('Custom Configuration',
        initial = {'appurl' : '',
                        'configuration-definition' : {
                        },
                        'configuration' : {
                            'debug' : 'true',
                            'auto_load' : 'true',
                            'actionlogging' : 'consoleShort',
                            'show_prompts' : 'true',
                            'textarea_concepts' : 'true',
                            'combobox_concepts' : 'true',
                            'drop_external' : 'true',
                            'concepts' : '',
                            'relations' : ''
                        }
                })

# Configuration definition: parameter for the script tag
# Configuration: values to read from the file.
# The default value of each variable is included in the definition.

def retrieve_url(url):
    """
    Retrieves the contents from a URL.
    @param url: URL to open.
    @return: Contents of the response.
    """

    if not url.startswith(('http://', 'https://')):
        raise Exception("Relative URLs are not accepted.")

    req = urllib2.Request(url)
    try:
        resp = urllib2.urlopen(req, None, timeout=3)
    except socket.timeout:
        print 'Timeout opening socket on remote host: ', url
    except urllib2.URLError as e:
        if hasattr(e, 'reason'):
            print 'We failed to reach a server.'
            print 'Reason: ', e.reason
        elif hasattr(e, 'code'):
            print 'The server couldn\'t fulfill the request.'
            print 'Error code: ', e.code
    else:
        if resp.info().gettype() == 'text/html':
            #convert to string:
            contents = resp.read()
            #close file because we dont need it anymore:
            resp.close()
            
            return contents

        else:
            print 'The document format is not supported'


@adaptor.edit_route
def edit(app_id):
    # Load data from the database for this application
    data = adaptor.load_data(app_id)

    if data['appurl'] == '' and request.method == 'POST':
        appurl = request.form['appurl']
        retrieve_url(appurl)

        # Store it in the database
        data['appurl'] = appurl
        data.update({
            'appurl': appurl})
        
        adaptor.save_data(app_id, data)
        flash("Configuration loaded successfully", "success")

    return render_template("custom_configuration/edit.html", appurl = data['appurl'], debug = data['configuration']['debug'],
                auto_load = data['configuration']['auto_load'], actionlogging = data['configuration']['actionlogging'],
                show_prompts = data['configuration']['show_prompts'], textarea_concepts = data['configuration']['textarea_concepts'],
                combobox_concepts = data['configuration']['combobox_concepts'], drop_external = data['configuration']['drop_external'],
                concepts = data['configuration']['concepts'], relations = data['configuration']['relations'])


@adaptor.route("/appdata/<app_id>/configuration.js", methods = ['GET'])
def load_configuration(app_id):
    """
    load_configuration(app_id)
    This function provides the default configuration of the tool.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.
    @return: The response with the current values stored in the configuration
    """

    data = adaptor.load_data(app_id)

    debug = json.dumps(data['configuration']["debug"])
    auto_load = json.dumps(data['configuration']["auto_load"])
    actionlogging = json.dumps(data['configuration']["actionlogging"])
    show_prompts = json.dumps(data['configuration']["show_prompts"])
    textarea_concepts = json.dumps(data['configuration']["textarea_concepts"])
    combobox_concepts = json.dumps(data['configuration']["combobox_concepts"])
    drop_external = json.dumps(data['configuration']["drop_external"])

    concepts = json.dumps([ s.strip() for s in data['configuration']["concepts"].split(',') ])
    relations = json.dumps([ s.strip() for s in data['configuration']["relations"].split(',') ])

    return render_template("custom_configuration/configuration_default.js", debug = debug, auto_load = auto_load, actionlogging = actionlogging,
                                            show_prompts = show_prompts, textarea_concepts = textarea_concepts, combobox_concepts = combobox_concepts,
                                            drop_external = drop_external, concepts = concepts, relations = relations)


    #CLEAN THIS CODE!!!!!!!!!!!!! THINK FOR DATA.VALUES IN VIEW  
"""
import re
import json
import urllib
import urlparse

def extract_base_url(url):
    parsed = urlparse.urlparse(url)
    new_path = parsed.path
    # Go to the last directory
    if '/' in new_path:
        new_path = new_path[:new_path.rfind('/')+1]
    messages_file_parsed = urlparse.ParseResult(scheme = parsed.scheme, netloc = parsed.netloc, path = new_path, params = '', query = '', fragment = '')
    return messages_file_parsed.geturl()

uno = extract_base_url('http://www.google.es/tarea/ruta.html')
print uno
"""

def parse_url(url):
    """
    Parses the contents from a URL.
    @param url: URL to open.
    @return: Contents of the response.
    """
    parsed = urlparse.urlparse(url)
    domain = parsed.netloc
    return domain


def extract_base_url(url):
    parsed = urlparse.urlparse(url)
    new_path = parsed.path
    # Go to the last directory
    if '/' in new_path:
        new_path = new_path[:new_path.rfind('/')+1]
    messages_file_parsed = urlparse.ParseResult(scheme = parsed.scheme, netloc = parsed.netloc, path = new_path, params = '', query = '', fragment = '')
    return messages_file_parsed.geturl()
    

def make_url_absolute(relative_path, url):
    if relative_path.startswith(('http://', 'https://')):
        return relative_path
    return _extract_base_url(url) + relative_path



