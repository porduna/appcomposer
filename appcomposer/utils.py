import re
import json
import traceback
import urlparse
from flask import request

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

SRC_REGEXP = re.compile(r"""(\s(src|href)\s*=\s*"?'?)(?!http://|https://|#|"|"#|'|'#| )""")

def inject_absolute_urls(output_xml, url):
    base_url = extract_base_url(url)
    return SRC_REGEXP.sub(r"\1%s" % base_url, output_xml)

def inject_original_url_in_xmldoc(xmldoc, url):
    contents = xmldoc.getElementsByTagName("Content")
    for content in contents:
        text_node = xmldoc.createCDATASection("""
        <script>
            if (typeof gadgets !== "undefined" && gadgets !== null) {
                gadgets.util.getUrlParameters().url = "%s";
            }
        </script>
        """ % url)
        content.insertBefore(text_node, content.firstChild)

def inject_absolute_locales_in_xmldoc(xmldoc, url):
    locales = xmldoc.getElementsByTagName("Locale")
    for loc in locales:
        messages_url = loc.getAttribute("messages")
        new_messages_url = make_url_absolute(messages_url, url)
        if new_messages_url != messages_url:
            loc.setAttribute("messages", new_messages_url)

def get_json():
    if request.json is not None:
        return request.json
    else:
        try:
            if request.data:
                data = request.data
            else:
                keys = request.form.keys() or ['']
                data = keys[0]
            return json.loads(data)
        except:
            print "Invalid JSON found"
            print "Suggested JSON: %r" % data
            traceback.print_exc()
            return None
