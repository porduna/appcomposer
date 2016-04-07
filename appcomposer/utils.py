import re
import json
import pprint
import traceback
import urlparse
import smtplib
from flask import request
from functools import wraps

def sendmail(subject, body, additional_recipients = None):
    from appcomposer.application import app
    MAIL_TPL = """From: App Composer <%(sender)s>
To: %(recipients)s
Subject: %(subject)s

%(body)s
"""
    smtp_server = app.config.get("SMTP_SERVER")
    from_addr = app.config.get("SENDER_ADDR")
    to_addrs = app.config.get("ADMINS")
    if not smtp_server or not from_addr or not to_addrs:
        return

    to_addrs = list(to_addrs)
    if additional_recipients is not None:
        to_addrs.extend(additional_recipients)

    server = smtplib.SMTP(smtp_server)

    server.sendmail(from_addr, to_addrs, MAIL_TPL % {
                'sender'     : from_addr,
                'recipients' : ', '.join(to_addrs),
                'subject'    : subject,
                'body'       : body.encode('utf8')
        })

def report_error(subject, body = "Error", additional_recipients = None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except:
                environ = pprint.pformat(request.environ)
                sendmail(subject, '{0}:\n\nFunction: {1}\n\nEnvironment:\n\n{2}\n\nStack trace:\n\n{3}'.format(body, f.__name__, environ, traceback.format_exc()), additional_recipients = additional_recipients)
                return 'Error. Administrator contacted'
        return wrapper
    return decorator

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

def get_original_url(xmldoc, default_url = None):
    app_composer_tags = xmldoc.getElementsByTagName("AppComposer")
    for app_composer_tag in app_composer_tags:
        if app_composer_tag.hasAttribute('originalUrl'):
            return app_composer_tag.getAttribute('originalUrl')
    return default_url

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
