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

def generate_side_effects():

    TWENTE_LIST = """common_en_ALL.xml\r\ncommon_es_ALL.xml\r\n"""


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

    # Regular messages
    BASIC_MESSAGE_BUNDLE_ENGLISH = """
    <messagebundle>
      <msg name="message1_{n}">Message1_{n}</msg>
      <msg name="message2_{n}">Message2_{n}</msg>
      <msg name="message3_{n}">Message3_{n}</msg>
      <msg name="message4_{n}">Message4_{n}</msg>
    </messagebundle>
    """

    # Message 4 is missing
    BASIC_MESSAGE_BUNDLE_SPANISH = """
    <messagebundle>
      <msg name="message1_{n}">Mensaje1_{n}</msg>
      <msg name="message2_{n}">Mensaje2_{n}</msg>
      <msg name="message3_{n}">Mensaje3_{n}</msg>
    </messagebundle>
    """

    # automatic=false messages
    NON_AUTOMATIC_BASIC_MESSAGE_BUNDLE_ENGLISH = """
    <messagebundle automatic="false">
      <msg name="message1_{n}">NonAutomaticMessage1_{n}</msg>
      <msg name="message2_{n}">NonAutomaticMessage2_{n}</msg>
      <msg name="message3_{n}">NonAutomaticMessage3_{n}</msg>
      <msg name="message4_{n}">NonAutomaticMessage4_{n}</msg>
    </messagebundle>
    """

    # Message 4 is missing
    NON_AUTOMATIC_BASIC_MESSAGE_BUNDLE_SPANISH = """
    <messagebundle>
      <msg name="message1_{n}">NonAutomaticMensaje1_{n}</msg>
      <msg name="message2_{n}">NonAutomaticMensaje2_{n}</msg>
      <msg name="message3_{n}">NonAutomaticMensaje3_{n}</msg>
    </messagebundle>
    """

    TOOL_ID_MESSAGE_BUNDLE_ENGLISH = """
    <messagebundle>
      <msg toolId="common" name="message1_{n}">ToolIdMessage1_{n}</msg>
      <msg toolId="common" name="message2_{n}">ToolIdMessage2_{n}</msg>
      <msg toolId="does.not.exist" name="message3_{n}">ToolIdMessage3_{n}</msg>
      <msg toolId="tool" name="message4_{n}">ToolIdMessage4_{n}</msg>
      <msg name="message5_{n}">ToolIdMessage5_{n}</msg>
      <msg name="message6_{n}">ToolIdMessage6_{n}</msg>
    </messagebundle>
    """

    # Message 6 is missing
    TOOL_ID_MESSAGE_BUNDLE_SPANISH = """
    <messagebundle>
      <msg name="message1_{n}">ToolIdMensaje1_{n}</msg>
      <msg name="message2_{n}">ToolIdMensaje2_{n}</msg>
      <msg name="message3_{n}">ToolIdMensaje3_{n}</msg>
      <msg name="message4_{n}">ToolIdMensaje4_{n}</msg>
      <msg name="message5_{n}">ToolIdMensaje5_{n}</msg>
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
            "app_image": "https://www.golabz.eu/logo%s.png" % app_id,
            "app_thumb": "https://www.golabz.eu/logo_thumb%s.png" % app_id,
            "app_golabz_page": "https://www.golabz.eu/apps/page%s" % app_id
        })

    # With prefix
    for pos, prefix in enumerate(('common_', 'tool_')):
        app_id = 3
        APPS.append({
            "title": "APP%s-%s" % (app_id, pos),
            "id": "%s-%s" % (app_id, pos),
            "author": "admin",
            "description": "DESCRIPTION%s" % app_id,
            "app_url": "http://url%s/%sgadget.xml" % (app_id, prefix),
            "app_type": "OpenSocial gadget",
            "app_image": "https://www.golabz.eu/logo%s.png" % app_id,
            "app_thumb": "https://www.golabz.eu/logo_thumb%s.png" % app_id,
            "app_golabz_page": "https://www.golabz.eu/apps/page%s-%s" % (app_id, pos)
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

    GADGETS.append({
        'http://url2/gadget.xml' : BASIC_GADGET_XML.format(language="""
                    <Locale messages="languages/en_ALL.xml" />
                    <Locale lang="en" messages="languages/en_ALL.xml" />
                    <Locale lang="es" messages="languages/es_ALL.xml" />
                """),
        'http://url2/languages/en_ALL.xml' : NON_AUTOMATIC_BASIC_MESSAGE_BUNDLE_ENGLISH.format(n=2),
        'http://url2/languages/es_ALL.xml' : NON_AUTOMATIC_BASIC_MESSAGE_BUNDLE_SPANISH.format(n=2),
    })

    # Two different apps with shared common code. File 1
    GADGETS.append({
        'http://url3/tool_gadget.xml' : BASIC_GADGET_XML.format(language="""
                    <Locale messages="languages/tool_en_ALL.xml" />
                    <Locale lang="en" messages="languages/tool_en_ALL.xml" />
                    <Locale lang="es" messages="languages/tool_es_ALL.xml" />
                """),
        'http://url3/languages/tool_en_ALL.xml' : TOOL_ID_MESSAGE_BUNDLE_ENGLISH.format(n=3),
        'http://url3/languages/tool_es_ALL.xml' : TOOL_ID_MESSAGE_BUNDLE_SPANISH.format(n=3),
    })

    # Two different apps with shared common code. File 2
    GADGETS.append({
        'http://url3/common_gadget.xml' : BASIC_GADGET_XML.format(language="""
                    <Locale messages="languages/common_en_ALL.xml" />
                    <Locale lang="en" messages="languages/common_en_ALL.xml" />
                    <Locale lang="es" messages="languages/common_es_ALL.xml" />
                """),
        'http://url3/languages/common_en_ALL.xml' : TOOL_ID_MESSAGE_BUNDLE_ENGLISH.format(n=3),
        'http://url3/languages/common_es_ALL.xml' : TOOL_ID_MESSAGE_BUNDLE_SPANISH.format(n=3),
    })


    #############################################################
    # 
    # LABS
    # 

    LABS = []

    #############################################################
    # 
    # OTHER APPS
    #

    GADGETS.append({
        'http://composer.golabz.eu/graasp_i18n/' : BASIC_GADGET_XML.format(language="""
                    <Locale messages="languages/en_ALL.xml" />
                    <Locale lang="en" messages="languages/en_ALL.xml" />
                    <Locale lang="es" messages="languages/es_ALL.xml" />
                """),
        'http://composer.golabz.eu/graasp_i18n/languages/en_ALL.xml' : BASIC_MESSAGE_BUNDLE_ENGLISH.format(n=1),
        'http://composer.golabz.eu/graasp_i18n/languages/es_ALL.xml' : BASIC_MESSAGE_BUNDLE_SPANISH.format(n=1),
        'http://composer.golabz.eu/speakup_i18n/' : BASIC_GADGET_XML.format(language="""
                    <Locale messages="languages/en_ALL.xml" />
                    <Locale lang="en" messages="languages/en_ALL.xml" />
                """),
        'http://composer.golabz.eu/speakup_i18n/languages/en_ALL.xml' : BASIC_MESSAGE_BUNDLE_ENGLISH.format(n=1),
        'http://composer.golabz.eu/twente_commons/' : BASIC_GADGET_XML.format(language="""
                    <Locale messages="languages/en_ALL.xml" />
                    <Locale lang="en" messages="languages/en_ALL.xml" />
                """),
        'http://composer.golabz.eu/twente_commons/languages/en_ALL.xml' : BASIC_MESSAGE_BUNDLE_ENGLISH.format(n=1),
    })

    SIDE_EFFECT_STRINGS = {
        "http://graasp.eu/token": json.dumps({'access_token': 'foo', 'refresh_token': 'bar'}),
        "http://graasp.eu/users/me": json.dumps(dict(username="Test User", email="appcomposer@go-lab-project.eu")),
        "https://www.golabz.eu/rest/apps/retrieve.json": json.dumps(APPS),
        "https://www.golabz.eu/rest/labs/retrieve.json": json.dumps(LABS),
        "http://go-lab.gw.utwente.nl/production/commons/languages/list.txt": TWENTE_LIST,
    }

    for gadget in GADGETS:
        SIDE_EFFECT_STRINGS.update(gadget)

    SIDE_EFFECT = {}
    for key, value in SIDE_EFFECT_STRINGS.items():
        SIDE_EFFECT[key] = _response(value)
    return SIDE_EFFECT

def create_requests_mock():
    side_effects = generate_side_effects()
    return mock.MagicMock(side_effect = lambda url, *args, **kwargs: side_effects.get(url))

