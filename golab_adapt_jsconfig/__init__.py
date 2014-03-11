import re
import urllib2
from flask import render_template, request, flash

from appcomposer.utils import make_url_absolute
from appcomposer.composers.adapt import create_adaptor

adaptor = create_adaptor('JavaScript configuration', 
                initial = {'url' : None})


CONFIG_DEFINITION_REGEX = re.compile("""(<\s*script[^<]+data-configuration-definition[^>]*>)""")
SRC_REGEX = re.compile("""src\s*=\s*["']?([^"']+)["']?""")

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


@adaptor.edit_route
def edit(app_id):
    # Load data from the database for this application
    data = adaptor.load_data(app_id)
        

    if request.method == 'POST':
        value = request.form['url']
        data['url'] = value
        # Store it in the database
        adaptor.save_data(app_id, data)

    url = data['url']
    definition_script = None

    if url and url.startswith(('http://', 'https://')):
        contents = urllib2.urlopen(url).read()
        definition_script = find_definition_script(contents, url)

    return render_template("jsconfig/edit.html",  
                                url = url or '',
                                definition_script = definition_script,
                                app_id = app_id)

@adaptor.route('/export/<app_id>/app.xml')
def app_xml(app_id):
    data = adaptor.load_data(app_id)
    return render_template("jsconfig/app.xml", 
                                url = data['url'])

@adaptor.route('/export/<app_id>/index.html')
def index_html(app_id):
    data = adaptor.load_data(app_id)
    # return render_template("jsconfig/simpletext.html",
    #                            url = data['url'])
    return "TO BE IMPLEMENTED"

