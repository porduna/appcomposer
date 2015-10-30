import mock
import json
import requests

############################################################
# 
# MISC
# 

def _response(contents):
    r = requests.Response()
    r._content = contents
    return r



BASIC_GADGET_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<Module>
    <ModulePrefs title="Action Statistics">
        <Require feature="osapi" />
        {language}
    </ModulePrefs>

    <Content type="html" view="default">
    </Content>
</Module>
"""

BASIC_MESSAGE_BUNDLE_ENGLISH = """
<messagebundle>
  <msg name="message1_{n}">Message1_{n}</msg>
  <msg name="message2_{n}">Message2_{n}</msg>
  <msg name="message3_{n}">Message3_{n}</msg>
</messagebundle>
"""

BASIC_MESSAGE_BUNDLE_SPANISH = """
<messagebundle>
  <msg name="message1_{n}">Mensaje1_{n}</msg>
  <msg name="message2_{n}">Mensaje2_{n}</msg>
  <msg name="message3_{n}">Mensaje3_{n}</msg>
</messagebundle>
"""

GADGETS = []

#############################################################
# 
# APPS
# 

APPS = []

for app_id in range(1, 10):
    APPS.append({
        "title": "APP%s" % app_id,
        "id": "%s" % app_id,
        "author": "admin",
        "description": "DESCRIPTION%s" % app_id,
        "app_url": "http://url%s/gadget.xml" % app_id,
        "app_type": "OpenSocial gadget",
        "app_image": "http://www.golabz.eu/logo%s.png" % app_id,
        "app_thumb": "http://www.golabz.eu/logo_thumb%s.png" % app_id,
        "app_golabz_page": "http://www.golabz.eu/apps/page%s" % app_id
    })

GADGETS.append({
    'http://url1/gadget.xml' : BASIC_GADGET_XML.format(language="""
                <Locale messages="languages/en_ALL.xml" />
                <Locale lang="en" messages="languages/en_ALL.xml" />
                <Locale lang="es" messages="languages/es_ALL.xml" />
            """),
    'http://url1/languages/en_ALL.xml' : BASIC_MESSAGE_BUNDLE_ENGLISH.format(n=1),
    'http://url1/languages/es_ALL.xml' : BASIC_MESSAGE_BUNDLE_SPANISH.format(n=1),
})

#############################################################
# 
# LABS
# 

LABS = []


SIDE_EFFECT_STRINGS = {
    "http://www.golabz.eu/rest/apps/retrieve.json": json.dumps(APPS),
    "http://www.golabz.eu/rest/labs/retrieve.json": json.dumps(LABS),
}

for gadget in GADGETS:
    SIDE_EFFECT_STRINGS.update(gadget)

SIDE_EFFECT = {}
for key, value in SIDE_EFFECT_STRINGS.items():
    SIDE_EFFECT[key] = _response(value)

def create_requests_mock():
    return mock.MagicMock(side_effect = lambda url, *args, **kwargs: SIDE_EFFECT.get(url))

