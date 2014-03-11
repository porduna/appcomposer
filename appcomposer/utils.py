import re
import urlparse

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

def inject_absolute_urls(self, output_xml, url):
    base_url = extract_base_url(url)
    return SRC_REGEXP.sub(r"\1%s" % base_url, output_xml)

