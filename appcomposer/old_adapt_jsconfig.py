import re
import json
import traceback
import urlparse
from xml.dom import minidom

from flask import render_template, url_for, Response, Blueprint

from appcomposer import db
from appcomposer.models import App
from appcomposer.translator.utils import get_cached_session

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
    return extract_base_url(url) + relative_path

SRC_REGEXP = re.compile(r"""(<\s*(?!ng-[^<]*)[^<]*\s(src|href)\s*=\s*"?'?)(?!http://|https://|#|"|"#|'|'#| )""")

def inject_absolute_urls(output_xml, url):
    base_url = extract_base_url(url)
    return SRC_REGEXP.sub(r"\1%s" % base_url, output_xml)

def inject_original_url_in_xmldoc(xmldoc, url):
    contents = xmldoc.getElementsByTagName("Content")
    original_url_node = xmldoc.createElement("AppComposer")
    original_url_node.setAttribute("originalUrl", url)

    for content in contents:
        text_node = xmldoc.createCDATASection("""
        <script>
            if (typeof gadgets !== "undefined" && gadgets !== null) {
                gadgets.util.getUrlParameters().url = "%s";
            }
        </script>
        """ % url)
        content.insertBefore(text_node, content.firstChild)
        content.parentNode.insertBefore(original_url_node, content)

def inject_absolute_locales_in_xmldoc(xmldoc, url):
    locales = xmldoc.getElementsByTagName("Locale")
    for loc in locales:
        messages_url = loc.getAttribute("messages")
        new_messages_url = make_url_absolute(messages_url, url)
        if new_messages_url != messages_url:
            loc.setAttribute("messages", new_messages_url)


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

        url = data['url'].strip()
        contents = get_cached_session().get(url).text

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

