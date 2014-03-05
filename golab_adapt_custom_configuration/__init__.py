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
# Configuration: values to read from the. T
# el valor predeterminado de cada variable (indicado en el definition)

def retrieve_url(url):
    """
    Retrieves the contents from a URL.
    @param url: URL to open.
    @return: Contents of the response.
    """

    if not url.startswith(('http://', 'https://')):
        raise Exception("Relative URLs are not accepted.")

    #TODO: errorhandler decorator to give the user nice error pages
    req = urllib2.Request(url)
    try:
        resp = urllib2.urlopen(req, None, timeout=3)
    except urllib2.URLError:
        print "The provided address is not responding", url
    except socket.timeout:
        print "Timeout opening socket on remote host:", url

    if resp.info().gettype() == 'text/html':
        contents = resp.read()
        return contents
        # Wip...
    else:
        print "The document format is not supported"


def parse_url(url):
    """
    Parses the contents from a URL.
    @param url: URL to open.
    @return: Contents of the response.
    """
    parsed = urlparse.urlparse(url)
    domain = parsed.netloc
    return domain


@adaptor.edit_route
def edit(app_id):
    # Load data from the database for this application
    data = adaptor.load_data(app_id)

    if request.method == 'POST':
        appurl = request.form['appurl']
        retrieve_url(appurl)

        data['appurl'] = appurl

        # Store it in the database
        data.update({
            'appurl': appurl})
        
        adaptor.save_data(app_id, data)
        flash("Configuration loaded successfully", "success")

    return render_template("custom_configuration/edit.html", appurl = data['appurl'],
                debug = data['configuration']['debug'], actionlogging = data['configuration']['actionlogging'],
                show_prompts = data['configuration']['show_prompts'], textarea_concepts = data['configuration']['textarea_concepts'],
                combobox_concepts = data['configuration']['combobox_concepts'], drop_external = data['configuration']['drop_external'],
                concepts = data['configuration']['concepts'], relations = data['configuration']['relations'])
