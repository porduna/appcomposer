import xml.etree.ElementTree as ET
import requests
from appcomposer import db, app
from appcomposer.models import App

with app.app_context():
    for app in db.session.query(App).filter_by(composer = 'translate'):
        owner_of_languages = []
        for appvar in app.appvars:
            if appvar.name == 'ownership':
                owner_of_languages.append(appvar.value)

        if owner_of_languages:
            # print app.spec.url
            xml_doc = requests.get(app.spec.url).text.encode('utf8')
            root = ET.fromstring(xml_doc)
            locales = root.findall('ModulePrefs')[0].findall('Locale')
            generic_locale_url = None
            for locale in locales:
                if 'lang' in locale.attrib:
                    continue
                generic_locale_url = locale.attrib['messages']
                break

            if generic_locale_url is None:
                continue

            base_url = app.spec.url.rsplit('/', 1)[0]
            original_locale_url = '/'.join((base_url, generic_locale_url))
            print original_locale_url
            # print len(requests.get(original_locale_url).text)
            for language in owner_of_languages:
                for bundle in app.bundles:
                    if bundle.lang == language:
                        for message in bundle.messages:
                            # print message.key
                            # print message.value
                            pass
