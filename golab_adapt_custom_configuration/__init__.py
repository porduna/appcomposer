import json
import urllib2
import urlparse
import socket

from HTMLParser import HTMLParser
from xml.etree import cElementTree as etree

from flask import render_template, request, flash
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

class HTML2Tree(HTMLParser):
    """
    A variant of HTMLParser that traverses a document
    and all its components: tags, attributes, text.
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self.tstack = etree.TreeBuilder()

    def handle_starttag(self, tag, attributes):
        self.tstack.start(tag, dict(attributes))

    def handle_endtag(self, tag):
        self.tstack.end(tag)

    def handle_data(self, data):
        self.tstack.data(data)

    def close(self):
        HTMLParser.close(self)
        return self.tstack.close()

def retrieve_url_response(url):
    """
    Retrieves the response from a URL.
    @param url: URL to open.
    @return: The response.
    """

    if not url.startswith(('http://', 'https://')):
        raise Exception('Relative URLs are not accepted.')

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
        # With a bad connection this instance returns
        # <AttributeError: 'NoneType' object has no attribute 'info'>
        if resp.info().gettype() == 'text/html' or 'text/xml':
            return resp
        else:
            print 'The document format is not supported'

def parse_html(resp):
    """
    Processes the response with text/html mimetype.
    @param url: HTTP response.
    @return: The HTML etree and its nodes.
    """
    #We've got a HTML response
    parser = HTML2Tree()
    parser.feed(resp.read())
    tree = parser.close()

    return tree

def parse_opensocial(resp):
    """
    Processes any response for OpenSocial text/html mimetype.
    @param url: HTTP response.
    @return: The HTML etree and its nodes.
    """
    #We've got a HTML fragment response
    #Extract the CDATA text from the etree Element
    xmltree = etree.parse(resp).getroot()
    cdata_content = xmltree.find('Content')
    htmlfragment = cdata_content.text

    #The CDATA block must be wrapped inside HTML tags to process its content
    l = []
    l.append('<html>')
    l.append(htmlfragment)
    l.append('</html>')
    wrappedhtml  = ''.join(l)

    parser = HTML2Tree()
    parser.feed(wrappedhtml)
    tree = parser.close()

    return tree

def get_definition_src(tree):
    """
    Explores a tree to find the script src.
    @param url: An ElementTree.
    @return: The src path.
    """
    for node in tree.findall('.//script'):
        if  node.attrib.has_key('data-configuration-definition'):
            srcpath = node.attrib.get('src')

    return srcpath

def parse_url(url):
    """
    Parses the contents from a URL.
    @param url: URL to open.
    @return: The base
    Example: http://domain.com/my/looong/path.html -> domain.com
    """
    parsed = urlparse.urlparse(url)
    domain = parsed.netloc
    return domain


def extract_base_url(url):
    """
    Parses the contents from a URL.
    @param url: URL to open.
    @return: The base
    Example: http://domain.com/1/2/3/path.html -> http://domain.com/1/2/3/
    """
    parsed = urlparse.urlparse(url)
    new_path = parsed.path
    # Go to the last directory
    if '/' in new_path:
        new_path = new_path[:new_path.rfind('/')+1]
    path_parsed = urlparse.ParseResult(scheme = parsed.scheme, netloc = parsed.netloc, path = new_path, params = '', query = '', fragment = '')
    return path_parsed.geturl()
    

def make_url_absolute(relative_path, url):
    if relative_path.startswith(('http://', 'https://')):
        return relative_path
    return extract_base_url(url) + relative_path


@adaptor.edit_route
def edit(app_id):
    # Load data from the database for this application
    data = adaptor.load_data(app_id)

    #The urlform is sent when the appurl is empty
    if request.method == 'POST':
        appurl = request.form['appurl']

        #Find the script src
        resp = retrieve_url_response(appurl)

        if resp.info().gettype() == 'text/html':
            tree = parse_html(resp)
            definition_src = get_definition_src(tree)
            
        elif resp.info().gettype() == 'text/xml':
            tree = parse_opensocial(resp)
            definition_src = get_definition_src(tree)

        print definition_src

        # Store the appurl and data definition in the database
        data['appurl'] = appurl
        data.update({
            'appurl': appurl})
        
        adaptor.save_data(app_id, data)
        flash('Configuration loaded successfully from: '+appurl, 'success')

    #The configuration settings form is shown in the other cases
    elif request.method == 'POST' and len(data['appurl']) != 0:

        # Retrieve the settings provided by the user
        # Variable name+supported values:
        # debug, auto_load, show_prompts, textarea_concepts, combobox_concepts, drop_external: "true" or "false" (double quotes included)
        # actionlogging: "null", "console", "consoleShort", "dufftown"(?!), "opensocial"

        debug = request.form['debug'] 
        auto_load = request.form['auto_load']
        actionlogging = request.form['actionlogging']
        show_prompts = request.form['show_prompts']
        textarea_concepts = request.form['textarea_concepts']
        combobox_concepts = request.form['combobox_concepts']
        drop_external = request.form['drop_external']
        concepts = ', '.join(list(OrderedDict.fromkeys([ s.strip() for s in request.form['concepts'].split(',') ])))
        relations = ', '.join(list(OrderedDict.fromkeys([ s.strip() for s in request.form['relations'].split(',') ])))

        # Build the configuration of the current concept map.
        data.update({
            'debug' : debug,
            'auto_load' : auto_load,
            'actionlogging' : actionlogging,
            'show_prompts' : show_prompts,
            'textarea_concepts' : textarea_concepts,
            'combobox_concepts' : combobox_concepts,
            'drop_external' : drop_external,
            'concepts': concepts,
            'relations': relations})

        adaptor.save_data(app_id, data)
        flash('Configuration saved successfully', 'success')
        
    return render_template("custom_configuration/edit.html", app_id = app_id, appurl = data['appurl'], debug = data['configuration']['debug'],
                auto_load = data['configuration']['auto_load'], actionlogging = data['configuration']['actionlogging'],
                show_prompts = data['configuration']['show_prompts'], textarea_concepts = data['configuration']['textarea_concepts'],
                combobox_concepts = data['configuration']['combobox_concepts'], drop_external = data['configuration']['drop_external'],
                concepts = data['configuration']['concepts'], relations = data['configuration']['relations'])


@adaptor.route("/export/<app_id>/")
def configeditor(app_id):
    """
    configeditor(app_id)
    This function points to the configeditor instance.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.
    @return: The webpage of a concept map.
    """

    return render_template("custom_configuration/configeditor.html", app_id = app_id)


@adaptor.route("/appdata/<app_id>/configuration.js", methods = ['GET'])
def load_configuration(app_id):
    """
    load_configuration(app_id)
    This function provides the default configuration of the tool.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.
    @return: The response with the current values stored in the configuration
    """

    data = adaptor.load_data(app_id)

    debug = json.dumps(data['configuration']['debug'])
    auto_load = json.dumps(data['configuration']["auto_load"])
    actionlogging = json.dumps(data['configuration']["actionlogging"])
    show_prompts = json.dumps(data['configuration']["show_prompts"])
    textarea_concepts = json.dumps(data['configuration']["textarea_concepts"])
    combobox_concepts = json.dumps(data['configuration']["combobox_concepts"])
    drop_external = json.dumps(data['configuration']["drop_external"])

    #Default values that overwrite the previous list for testing purposes
    data['configuration']['debug'] = 'true',
    data['configuration']['auto_load'] = 'true'
    data['configuration']['actionlogging'] = 'consoleShort'
    data['configuration']['show_prompts'] = 'true'
    data['configuration']['textarea_concepts'] = 'true'
    data['configuration']['combobox_concepts'] = 'true'
    data['configuration']['drop_external'] = 'true'     
    data['configuration']['concepts'] = "concept1,concept2,concept3"
    data['configuration']['relations'] = "rel1,rel2,rel3"

    concepts = json.dumps([ s.strip() for s in data['configuration']['concepts'].split(',') ])
    relations = json.dumps([ s.strip() for s in data['configuration']['relations'].split(',') ])

    #For now we use the configuration format available in 0.9.
    # The domain.js will be replaced later with the new one.
    return render_template("custom_configuration/domain.js", debug = debug, auto_load = auto_load, actionlogging = actionlogging,
                                            show_prompts = show_prompts, textarea_concepts = textarea_concepts, combobox_concepts = combobox_concepts,
                                            drop_external = drop_external, concepts = concepts, relations = relations)
