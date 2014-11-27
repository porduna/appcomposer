import re
import json
import urllib2
import traceback
from xml.dom import minidom

from flask import render_template, request, flash, url_for, Response
from flask_wtf import Form
from wtforms import TextField
from wtforms.validators import url as url_validator, required

from appcomposer.babel import gettext, lazy_gettext
from appcomposer.utils import make_url_absolute, inject_absolute_urls, get_json, inject_original_url_in_xmldoc, inject_absolute_locales_in_xmldoc
from appcomposer.composers.adapt import create_adaptor

adaptor = create_adaptor('Labs adaptation', 
                initial = {'url' : None, 'configuration' : None}, 
                description = lazy_gettext("Create adaptations of customizable gateway4labs laboratories."),
                about_endpoint = 'gateway4labs.about')

SHINDIG_SERVER = 'http://shindig2.epfl.ch'
def shindig_url(relative_url):
    return '%s%s' % (SHINDIG_SERVER, relative_url)

def replace_default_configuration_script(contents, new_url):
    return DEFAULT_CONFIG_REGEX.sub('<script data-configuration type="text/javascript" src="%s">' % new_url, contents)

class UrlForm(Form):
    # TODO: use the url_validator again
    url            = TextField(lazy_gettext(u'URL'), validators = [ required() ])
    # labmanager_url = TextField(lazy_gettext(u'Labmanager URL'), validators = [ url_validator() ])

@adaptor.edit_route
def edit(app_id):
    # Load data from the database for this application
    data = adaptor.load_data(app_id)
    new_url = False
    contents = None

    url_form = UrlForm()
    if not url_form.url.data:
        url_form.url.data = data['url']

    if request.method == 'POST':
        value = request.form['url']
        if value != data['url']:
            if url_form.validate_on_submit():
                # Reset the configuration
                data['url'] = value
                new_url = True
                data['configuration'] = None
                adaptor.save_data(app_id, data)
            else:
                print "Invalid"
                print url_form.url.errors
                print url_form.labmanager_url.errors

    url = data['url']
    configuration = json.dumps(data['configuration'], indent = 4)
    quoted_config = urllib2.quote(json.dumps(data['configuration']), '')

    return render_template("gateway4labs/edit.html",  
                                url = url or '',
                                app_id = app_id,
                                configuration = configuration,
                                quoted_config = quoted_config,
                                url_form = url_form,
                                name = adaptor.get_name(app_id))

@adaptor.route('/save/<app_id>/', methods = ['GET', 'POST'])
def save_json_config(app_id):
    # TODO: CSRF
    if request.method == 'POST':
        json_contents = get_json()
        if json_contents:
            print json_contents
            data = adaptor.load_data(app_id)
            data['configuration'] = json_contents
            flash("Saved")
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
        
        # If the user hasn't clicked on "Save" yet, do not replace configuration script
        if data.get('configuration_name'):
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
        return Response(contents, mimetype='text/xml')

@adaptor.route('/export/<app_id>/configuration.js')
def configuration(app_id):
    data = adaptor.load_data(app_id)
    name = data.get('configuration_name', 'missing-name')
    configuration = data.get('configuration', {})
    configuration_json = json.dumps(configuration, indent = 4)
    return render_template("gateway4labs/configuration.js", name = name, configuration = configuration_json)

@adaptor.route("/about")
def about():
    return render_template("gateway4labs/about.html")

@adaptor.route("/developers")
def developers():
    return render_template("gateway4labs/developers.html")

