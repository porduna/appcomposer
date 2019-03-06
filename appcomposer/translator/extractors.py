import json
import zlib
import time
import hashlib
import logging
import urlparse
import xml.etree.ElementTree as ET

from collections import namedtuple

import requests

from bs4 import BeautifulSoup

from selenium import webdriver

from appcomposer import redis_store, db
from appcomposer.application import SSL_DOMAIN_WHITELIST
from appcomposer.models import RepositoryApp
from appcomposer.exceptions import TranslatorError
from appcomposer.translator.utils import get_cached_session, fromstring, get_text_from_response

DEBUG = True

def extract_local_translations_url(app_url, force_local_cache = False):
    redis_key = 'appcomposer:fast-cache:{}'.format(app_url)

    if force_local_cache:
        # Under some situations (e.g., updating a single message), it is better to have a cache
        # than contacting the foreign server. Only if requested, this method will try to check
        # in a local cache in Redis.
        cached = redis_store.get(redis_key)
        if cached:
            translation_url, original_messages, metadata = json.loads(cached)
            if metadata is not None:
                original_messages_loaded = json.loads(original_messages)
                metadata_loaded = json.loads(metadata)
                return translation_url, original_messages_loaded, metadata_loaded

    cached_requests = get_cached_session()

    repository_app = db.session.query(RepositoryApp).filter_by(url=app_url).first()
    if repository_app is not None:
        guessing = False
        app_format = repository_app.app_format
    else:
        guessing = True
        app_url_path = urlparse.urlparse(app_url).path
        if app_url_path.endswith('.xml'):
            app_format = 'opensocial'
        elif app_url_path.endswith('.html'):
            app_format = 'html'
        else:
            r = cached_requests.get(app_url)
            if 'xml' in (r.headers.get('Content-Type') or ''):
                app_format = 'opensocial'
            else:
                app_format = 'html'

    if app_format == 'opensocial' or not app_format: # Default to opensocial
        try:
            app_information = _extract_information_opensocial(app_url, cached_requests)
        except TranslatorError as err:
            if not guessing:
                raise

            try:
                app_information = _extract_information_html(app_url, cached_requests)
            except TranslatorError as err2:
                raise TranslatorError("Error trying both opensocial and html: {} / {}".format(err, err2))
    else:
        try:
            app_information = _extract_information_html(app_url, cached_requests)
        except TranslatorError as err:
            try:
                app_information = _extract_information_opensocial(app_url, cached_requests)
            except TranslatorError as err2:
                raise TranslatorError("Error trying both html and opensocial: {} / ".format(err, err2))


    locales_without_lang = [ locale for locale in app_information.locales if not locale['lang'] or locale['lang'].lower() == 'all' ]
    if not locales_without_lang:
        raise TranslatorError("That application does not provide any default locale. The application has probably not been adopted to be translated.")

    relative_translation_url = locales_without_lang[0]['messages']
    if not relative_translation_url:
        raise TranslatorError("Default Locale not provided message attribute")

    absolute_translation_url, messages, metadata, contents = _retrieve_messages_from_relative_url(app_url, relative_translation_url, cached_requests)

    redis_value = json.dumps([
        absolute_translation_url,
        json.dumps(messages),
        json.dumps(metadata)
    ])
    redis_store.setex(name=redis_key, time=10 * 60, value=redis_value) # For 10 minutes
    return absolute_translation_url, messages, metadata

def extract_metadata_information(app_url, preview_link, cached_requests = None, force_reload = False, app_format=None):
    if cached_requests is None:
        cached_requests = get_cached_session()

    if not app_format or app_format == 'opensocial':
        app_information = _extract_information_opensocial(app_url, cached_requests)
    elif app_format == 'html':
        app_information = _extract_information_html(app_url, cached_requests)
    else:
        raise TranslatorError('Invalid app format: {}'.format(app_format))

    original_translations = {}
    original_translation_urls = {}
    default_translations = {}
    default_translation_url = None
    default_metadata = {}

    if len(app_information.locales) == 0:
        translatable = False
    else:
        translatable = True
        default_locale = None
        for locale in app_information.locales:
            lang = locale['lang']
            country = locale['country']
            messages_url = locale['messages']
            if lang and messages_url and lang.lower() != 'all':
                if country:
                    lang = u'{}_{}'.format(lang, country)
                elif len(lang) == 2:
                    lang = u'%s_ALL' % lang

                if lang.lower() == 'zh_all':
                    lang = 'zh_CN'
                if '_' in lang and lang.split('_')[0].lower() == lang.split('_')[1].lower():
                    # es_ES is es_ALL, fr_FR is fr_ALL
                    lang = '{}_ALL'.format(lang.split('_'))

                try:
                    absolute_url, messages, metadata, locale_contents = _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests)
                except TranslatorError as e:
                    logging.warning(u"Could not load %s translation for app URL: %s Reason: %s" % (lang, app_url, e), exc_info = True)
                    continue
                else:
                    new_messages = {}
                    if messages:
                        for key, value in messages.iteritems():
                            new_messages[key] = value['text']
                    original_translations[lang] = new_messages
                    original_translation_urls[lang] = absolute_url

            if (lang is None or lang.lower() == 'all') and messages_url:
                # Process this later. This way we can force we get the results for the default translation
                default_locale = locale

        if default_locale is not None:
            messages_url = default_locale['messages']
            absolute_url, messages, metadata, locale_contents = _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests)
            default_translations = messages
            default_translation_url = absolute_url
            default_metadata = metadata

            # No English? Default is always English!
            if 'en_ALL' not in original_translations:
                lang = 'en_ALL'
                new_messages = {}
                if messages:
                    for key, value in messages.iteritems():
                        new_messages[key] = value['text']

                original_translations[lang] = new_messages
                original_translation_urls[lang] = absolute_url

    check_urls = app_information.check_urls
    if preview_link:
        check_urls.append(preview_link)

    metadata = {
        'translatable' : translatable,
        'check_urls' : check_urls,
        'uses_proxy': app_information.uses_proxy,
        'adaptable' : False, # Not supported anymore (all 0 in the database right now)
        'original_translations' : original_translations,
        'original_translation_urls' : original_translation_urls,
        'default_translations' : default_translations,
        'default_translation_url' : default_translation_url,
        'default_metadata' : default_metadata,
    }

    translation_hash, serialized = _calculate_translations_hash(original_translations, default_translations)
    metadata['translation_hash'] = translation_hash
    metadata['check_urls_hash'] = unicode(zlib.crc32(json.dumps(sorted(check_urls))))
    return metadata

def _calculate_translations_hash(original_translations, default_translations):
    values = [
        # [
        #     lang,
        #     [('category', None), ('tool_id', None)...] # Sorted by key
        # ]
    ]
    for term, term_data in default_translations.items():
        listed_data = sorted(list(term_data.items()), lambda (k1, v1), (k2, v2): cmp(k1, k2))
        values.append([ term, listed_data ])

    for lang, lang_data in original_translations.items():
        listed_data = sorted(list(lang_data.items()), lambda (k1, v1), (k2, v2): cmp(k1, k2))
        values.append([ lang, listed_data])

    values.sort(lambda (k1, v1), (k2, v2): cmp(k1, k2))

    contents = json.dumps(values)
    return unicode(zlib.crc32(contents)), contents


def extract_messages_from_translation(messages_absolute_url, xml_contents):
    contents = fromstring(xml_contents)
    messages = {}
    attribs = dict(contents.attrib)
    if 'namespace' in contents.attrib:
        default_namespace = contents.attrib['namespace']
    else:
        default_namespace = None

    if 'mails' in contents.attrib:
        mails = [ mail.strip() for mail in contents.attrib['mails'].split(',') ]
    else:
        mails = []

    automatic = contents.attrib.get('automatic', 'true').lower() == 'true'

    for pos, xml_msg in enumerate(contents.findall('msg')):
        if 'name' not in xml_msg.attrib:
            raise TranslatorError("Invalid translation file: no name in msg tag")

        name = xml_msg.attrib['name']

        if 'category' in xml_msg.attrib:
            category = xml_msg.attrib['category']
        else:
            category = None

        if 'format' in xml_msg.attrib:
            format = xml_msg.attrib['format']
        else:
            format = "plain"

        if 'namespace' in xml_msg.attrib:
            namespace = xml_msg.attrib['namespace']
        else:
            namespace = default_namespace

        # if not category and namespace:
        #     category = namespace

        same_tool = True
        if 'toolId' in xml_msg.attrib:
            tool_id = xml_msg.attrib['toolId']
            if tool_id:
                basename = messages_absolute_url.rsplit('/', 1)[1]
                if not basename.lower().startswith(tool_id.lower()):
                    same_tool = False
                hostname = urlparse.urlparse(messages_absolute_url).netloc
                # We generate the namespace based on the hostname. But localhost:5000 and composer.golabz.eu has a special hostname
                if messages_absolute_url.startswith(('http://localhost:5000/twente_commons/', 'http://composer.golabz.eu/twente_commons/')):
                    hostname = 'go-lab.gw.utwente.nl'
                namespace = "{0}::{1}".format(hostname, tool_id)
        else:
            tool_id = None

        # Some people use things like <msg name='foo'>Press <i class=''></i> to ...</msg>
        # This is invalid XML, but we want to support it too. So:
        try:
            # Get whatever is between the <msg name='foo'> and </msg>:
            raw_msg_message = ET.tostring(xml_msg).split(">", 1)[1].rsplit("<", 1)[0]
        except IndexError:
            # If this ever happens, forget about it
            raw_msg_message = ""

        if '<' in raw_msg_message or '>' in raw_msg_message:
            xml_text = raw_msg_message
        else:
            # However, we also want to support people using &lt;i class=''&gt;, so the
            # code above is only used if < or > are present in the text. Otherwise we
            # trust the XML library
            xml_text = xml_msg.text or ""

        messages[name] = {
            'text' : xml_text,
            'category' : category,
            'namespace' : namespace,
            'position' : pos,
            'same_tool' : same_tool,
            'tool_id' : tool_id,
            'format': format,
        }
    metadata = {
        'mails' : mails,
        'automatic' : automatic,
        'attribs' : json.dumps(attribs),
    }
    return messages, metadata

def _raise_for_status(url, response):
    if response is None:
        raise requests.RequestException("URL: {0}: Expected response, returned None (probably in tests)".format(url))
    response.raise_for_status()

class AppInformation(namedtuple("AppInformation", ['locales', 'check_urls', 'uses_proxy'])):
    pass

def _extract_information_opensocial(app_url, cached_requests):
    try:
        response = cached_requests.get(app_url, timeout = 30)
        _raise_for_status(app_url, response)
        xml_contents = get_text_from_response(response)
    except requests.RequestException as e:
        logging.warning(u"Could not load this app URL (%s): %s" % (app_url, e), exc_info = True)
        raise TranslatorError(u"Could not load this app URL: %s" % e)

    try:
        root = fromstring(xml_contents)
    except Exception as e:
        logging.warning(u"Invalid XML document (%s): %s" % (app_url, e), exc_info = True)
        print(u"Invalid XML document (%s): %s" % (app_url, e))
        raise TranslatorError("Invalid XML document: %s" % e)

    module_prefs = root.findall("ModulePrefs")
    if not module_prefs:
        raise TranslatorError("ModulePrefs not found in App URL")

    check_urls = [ app_url ] # The app_url itself is always a URL to check
    uses_proxy = False
    for appcomposer_tag in module_prefs[0].findall('appcomposer'):
        check_url = appcomposer_tag.attrib.get('check-url')
        if check_url:
            check_urls.append(check_url)

        uses_proxy_str = appcomposer_tag.attrib.get('uses-proxy')
        if uses_proxy_str:
            uses_proxy = uses_proxy_str.lower() in ['1', 'true', 'yes']

    check_urls.sort()

    xml_locales = module_prefs[0].findall('Locale')
    locales = []
    for xml_locale in xml_locales:
        locale = {
            'lang': xml_locale.attrib.get('lang'),
            'country': xml_locale.attrib.get('country'),
            'messages': xml_locale.attrib.get('messages'),
        }
        locales.append(locale)
    
    return AppInformation(locales=locales, check_urls=check_urls, uses_proxy=uses_proxy)

def _extract_information_html(app_url, cached_requests):
    try:
        response = cached_requests.get(app_url, timeout = 30)
        _raise_for_status(app_url, response)
        html_contents = get_text_from_response(response)
    except requests.RequestException as e:
        logging.warning(u"Could not load this app URL (%s): %s" % (app_url, e), exc_info = True)
        raise TranslatorError(u"Could not load this app URL: %s" % e)

    soup = BeautifulSoup(html_contents, 'lxml')

    check_urls = [ app_url ] # The app_url itself is always a URL to check

    for check_url_tag in soup.find_all('meta', attrs=dict(name='check-url')):
        check_url = check_url_tag.get('value')
        if check_url:
            check_urls.append(check_url)

    check_urls.sort()

    locales = []
    for translations_meta in soup.find_all('meta', attrs=dict(name='translations')):
        locale = {
            'lang': translations_meta.get('lang'),
            'country': translations_meta.get('country'),
            'messages': translations_meta.get('messages') or translations_meta.get('value')
        }
        locales.append(locale)

    uses_proxy_metas = soup.find_all('meta', atts=dict(name='uses-proxy'))
    if uses_proxy_metas:
        # If there is more than one, check just the last one
        uses_proxy = (uses_proxy_metas[-1].get('value') or '').lower() in ['1', 'true', 'yes']
    else:
        uses_proxy = False

    if not locales and len(check_urls) == 1 and not uses_proxy_metas:
        # If it's just a random HTML document... it is probably an error
        logging.warning(u"Invalid HTML document (%s): missing tags" % app_url)
        print(u"Invalid HTML document (%s): missing tags" % app_url)
        raise TranslatorError("Invalid HTML document: missing tags")

    return AppInformation(locales=locales, check_urls=check_urls, uses_proxy=uses_proxy)

def _retrieve_messages_from_relative_url(app_url, messages_url, cached_requests):
    if messages_url.startswith(('http://', 'https://', '//')):
        absolute_translation_url = messages_url
    else:
        base_url = app_url.rsplit('/', 1)[0]
        absolute_translation_url = '/'.join((base_url, messages_url))

    try:
        translation_messages_response = cached_requests.get(absolute_translation_url, timeout = 30)
        _raise_for_status(absolute_translation_url, translation_messages_response)
        translation_messages_xml = get_text_from_response(translation_messages_response)
    except Exception as e:
        logging.warning("Could not reach locale URL: %s  Reason: %s" % (absolute_translation_url, e), exc_info = True)
        raise TranslatorError("Could not reach locale URL")

    # XXX TODO: Remove this list
    if absolute_translation_url.startswith('http://go-lab.gw.utwente.nl/production/'):
        translation_messages_xml = translation_messages_xml.replace("<messagebundle>", '<messagebundle mails="pablo.orduna@deusto.es">')

    try:
        messages, metadata = extract_messages_from_translation(absolute_translation_url, translation_messages_xml)
    except TranslatorError as e:
        logging.warning("Could not load XML contents from %s Reason: %s" % (absolute_translation_url, e), exc_info = True)
        raise TranslatorError("Could not load XML in %s" % absolute_translation_url)

    return absolute_translation_url, messages, metadata, translation_messages_xml

def extract_check_url_metadata(url, uses_proxy):
    failed = False
    flash = None
    ssl = None
    proxy_works = None
    proxy_image_stored = False
    error_message = None
    headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64 GOLAB APP COMPOSER) AppleWebKit/537.36 (KHTML, like Gecko)'}
    try:
        req = requests.get(url, allow_redirects=True, timeout=(15,15), headers=headers)
        req.raise_for_status()
    except Exception as err:
        failed = True
        error_message = str(err)
    else:
        content = req.content or ''
        if not flash:
            if url.endswith('.swf'):
                flash = True
            elif 'shockwave' in (req.headers.get('Content-Type') or ''):
                flash = True
            elif 'download.macromedia.com' in content:
                flash = True
            elif 'macromedia.com/go/getflashplayer' in content:
                flash = True
            elif 'flash.embedFlash' in content:
                flash = True

        if "This webpage was generated by the domain owner using" in content and "Sedo Domain Parking" in content and "This website allows third-party advertising" in content:
            # Spammers who buy expired domains provide a proper website and return 200 OK to any URL.
            failed = True

        content_size = len(content)

        parsed_url = urlparse.urlparse(url)
        url_in_whitelist = parsed_url.netloc in SSL_DOMAIN_WHITELIST
    
        if url.startswith('https://') or uses_proxy or url_in_whitelist:
            ssl = True
        else:
            ssl_url = url.replace('http://', 'https://', 1)

            try:
                req = requests.get(ssl_url, allow_redirects=True, timeout=(15,15), headers=headers)
                req.raise_for_status()
            except Exception as err:
                ssl = False
            else:
                ssl_content = req.content or ''
                # +- 10% since sometimes it includes https URLs
                if content_size * 0.9 <= len(ssl_content) <= content_size * 1.1:
                    ssl = True

            if not ssl:
                result = _check_proxy(url)
                proxy_works = result['equals']
                proxy_image_stored = result['stored']

    return {
        'failed': failed,
        'flash': flash,
        'ssl': ssl,
        'error_message': error_message,
        'proxy_image_works': proxy_works,
        'proxy_image_stored': proxy_image_stored,
    }

def _check_proxy(url):
    return {
        'stored': False,
        'equals': False,
    }

    # It works but ssl is not working. Time to check whether in phantomjs it's the same thing or not
    cap = webdriver.DesiredCapabilities.PHANTOMJS
    cap["phantomjs.page.settings.resourceTimeout"] = 1000
    cap["phantomjs.page.settings.loadImages"] = False
    cap["phantomjs.page.settings.userAgent"] = 'Mozilla/5.0 (X11; Linux x86_64 GOLAB APP COMPOSER) AppleWebKit/537.36 (KHTML, like Gecko)'
    driver = webdriver.PhantomJS(desired_capabilities=cap)
    driver.implicitly_wait(15)
    driver.set_page_load_timeout(15)
    hashed = hashlib.new("md5", url).hexdigest()
    file_path_with_proxy = 'appcomposer/static/proxy-images/{}_proxy.png'.format(hashed)
    file_path_without_proxy = 'appcomposer/static/proxy-images/{}_non-proxy.png'.format(hashed)
    stored = False
    try:
        driver.get(url)
        time.sleep(3)
        driver.save_screenshot(file_path_without_proxy)
        driver.get('https://gateway.golabz.eu/proxy/' + url)
        time.sleep(3)
        driver.save_screenshot(file_path_with_proxy)
        stored = True
    except:
        pass
    finally:
        try:
            driver.close()
        except:
            pass

    files_are_equal = False
    if stored:
        contents_with_proxy = hashlib.new('md5', open(file_path_with_proxy).read()).hexdigest()
        contents_without_proxy = hashlib.new('md5', open(file_path_without_proxy).read()).hexdigest()
        files_are_equal = contents_with_proxy == contents_without_proxy

    return {
        'stored': stored,
        'equals': files_are_equal,
    }
