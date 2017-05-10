import re
import json
import urllib2
import traceback
from xml.dom import minidom

from flask import render_template, url_for, Response, Blueprint

from appcomposer import db
from appcomposer.models import App
from appcomposer.utils import inject_absolute_urls, inject_original_url_in_xmldoc, inject_absolute_locales_in_xmldoc

old_adapt_jsconfig = Blueprint(__name__, 'adapt')

DEFAULT_CONFIG_REGEX = re.compile(r"""(<\s*script[^<]*\sdata-configuration(?:>|\s[^>]*>))""")

def replace_default_configuration_script(contents, new_url):
    return DEFAULT_CONFIG_REGEX.sub('<script data-configuration type="text/javascript" src="%s">' % new_url, contents)

@old_adapt_jsconfig.route('/export/<app_id>/app.xml')
def app_xml(app_id):
    try:
        app = db.session.query(App).filter_by(unique_id=app_id, composer = 'adapt').first()
        if app is None:
            return "App not found", 404

        data = json.loads(app.data)
        if data['adaptor_type'] != 'jsconfig':
            return "App deprecated", 404

        url = data['url']
        contents = urllib2.urlopen(url).read()

        # If the user hasn't clicked on "Save" yet, do not replace configuration script
        if data.get('configuration_name'):
            contents = replace_default_configuration_script(contents,
                                                            url_for('.configuration', app_id=app_id, _external=True))

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


@old_adapt_jsconfig.route('/export/<app_id>/configuration.js')
def configuration(app_id):
    app = db.session.query(App).filter_by(unique_id=app_id, composer = 'adapt').first()
    if app is None:
        return "App not found", 404

    data = json.loads(app.data)
    if data['adaptor_type'] != 'jsconfig':
        return "App deprecated", 404

    name = data.get('configuration_name', 'missing-name')
    configuration = data.get('configuration', {})
    configuration_json = json.dumps(configuration, indent=4)
    return render_template("jsconfig/configuration.js", name=name, configuration=configuration_json)

