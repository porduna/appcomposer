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

    return render_template("custom_configuration/edit.html", appurl = data['appurl'],
                debug = data['configuration']['debug'], actionlogging = data['configuration']['actionlogging'],
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

    debug = json.dumps(data["debug"])
    auto_load = json.dumps(data["auto_load"])
    actionlogging = json.dumps(data["actionlogging"])
    show_prompts = json.dumps(data["show_prompts"])
    textarea_concepts = json.dumps(data["textarea_concepts"])
    combobox_concepts = json.dumps(data["combobox_concepts"])
    drop_external = json.dumps(data["drop_external"])

    concepts = json.dumps([ s.strip() for s in data["concepts"].split(',') ])
    relations = json.dumps([ s.strip() for s in data["relations"].split(',') ])

    return render_template("custom_configuration/configuration_default.js", debug = debug, actionlogging = actionlogging, show_prompts = show_prompts,
                                            textarea_concepts = textarea_concepts, combobox_concepts = combobox_concepts, drop_external = drop_external,
                                            concepts = concepts, relations = relations)
