import json
import os
import urllib
from flask import make_response
from markupsafe import Markup
from sqlalchemy.util import deprecated
from appcomposer.appstorage.api import get_app
from appcomposer.composers.translate import translate_blueprint
from xml.dom import minidom
import StringIO


"""
NOTE:
The current design for the export system is the following. Included here for reference purposes.
In the future it may be modified, as it has some issues / limitations.

NEW_APP()
 - GET OriginalSpec
 - GET OriginalXMLs
 - CREATE InternalJSONs

EDIT_APP()
 - GET OriginalSpec
 - GET OriginalXMLs
 - GET InternalJSONs
 - EDIT InternalJSONs
 - SAVE InternalJSONs

SERVE_APP()
 - GET OriginalSpec
 - GET InternalJSONs
 - SERVE OriginalBaseTranslation
 - SERVE JSONInternalTranslation
 """


class NoDefaultLanguageException(Exception):
    """
    Exception to be thrown when an App specified to be translated does not have a default translation.
    (And hence it is probably not ready to be translated).
    """
    def __init__(self, message=None):
        self.message = message

class ExternalFileRetrievalException(Exception):
    """
    Exception to be thrown when an operation failed because it was not possible to retrieve a file
    from an external host.
    """
    def __init__(self, message=None):
        self.message = message


class BundleManager(object):
    """
    To manage the set of bundles for an App, and to provide common functionality.
    """

    def __init__(self, original_gadget_spec=None):
        self._bundles = {}

        # Points to the original gadget spec XML.
        self.original_gadget_spec = original_gadget_spec

        # TODO: Consider whether this should always be stored here.
        self.original_xml = None

        self._base_publish_url = "LOCALHOST"  # This is to be changed.

    def load_app(self, app):
        """
        Loads an App object.
        TODO: Not yet clear in which state the object should be before loading.
        @param app: The App object to load
        @return: None. App is internally loaded into de manager.
        """
        self.from_json(app.data)
        # Not yet fully implemented.


    def _read_url(self, url):
        """
        Simply retrieves a specified URL (Synchronously).
        @param url: URL to retrieve.
        @return: Contents of the URL.
        """
        handle = urllib.urlopen(url)
        contents = handle.read()
        return contents

    def _load_spec(self, url):
        """
        Fully loads the specified gadget spec.
        @param url: URL to the XML Gadget Spec.
        @return: Nothing. The bundles are internally stored once parsed.
        """

        # Store the specified URL as the gadget spec.
        self.original_gadget_spec = url

        xml_str = self._read_url(url)
        self.original_xml = xml_str
        locales = self._extract_locales(xml_str)
        for loc in locales:
            bundle_xml = self._read_url(loc[2])
            bundle = Bundle.from_xml(bundle_xml, loc[0], loc[1])
            name = self.get_name(loc[0], loc[1])
            self._bundles[name] = bundle

    def to_json(self):
        """
        Exports everything to JSON.
        """
        data = {
            "spec": self.original_gadget_spec,
            "bundles": {}
        }
        for name, bundle in self._bundles.items():
            data["bundles"][name] = bundle.to_jsonable()
        return json.dumps(data)

    def from_json(self, json):
        """
        Loads the specified JSON into the BundleManager.
        @param json: JSON string to load.
        @return: Nothing
        """
        appdata = json.loads(json)
        bundles = appdata["bundles"]
        for name, bundledata in bundles.items():
            # TODO: Kludgey and inefficient. Fix/refactor this.
            bundlejs = json.dumps(bundledata)
            if name in self._bundles:
                bundle = self._bundles[name]
            else:
                pass
        raise Exception("Not yet implemented")


    def get_name(self, lang, country):
        """
        Gets a name in the form ca_ES.
        """
        if lang is None or lang == "":
            lang = "ANY"
        if country is None or country == "":
            country = "ANY"
        return "%s_%s" % (lang, country)

    def _extract_locales(self, xml_str):
        """
        Extracts the Locale nodes info from an xml_str (a gadget spec).
        """
        locales = []
        xmldoc = minidom.parseString(xml_str)
        itemlist = xmldoc.getElementsByTagName("Locale")
        for elem in itemlist:
            messages_file = elem.attributes["messages"].nodeValue

            try:
                lang = elem.attributes["lang"].nodeValue
            except KeyError:
                lang = ""

            try:
                country = elem.attributes["country"].nodeValue
            except KeyError:
                country = ""

            locales.append((lang, country, messages_file))
        return locales

    def _inject_locales_into_spec(self, host_url, xml_str, respect_default=True):
        """
        _inject_locales_into_spec(host_url, xml_str)

        Generates a new Gadget Spec from a provided Gadget Spec, replacing every original Locale with links
        to custom Locales, hosted at host_url.

        Optionally, it can avoid modifying the default translation.
        This is done so that if the original author updates the translation, this takes immediate effect
        into the translated versions of the App.

        @param host_url: Base URL that will host the language bundles' XML files. Generally, it will be an URL
        of the Composer itself, specific to the App, and dynamically generated.

        @param xml_str: String containing the XML of the original Gadget Spec.

        @param respect_default: If false, every Locale will be removed and replaced with custom links to the
        language, using the host_url as base. If true, the same will be done to every Locale, EXCEPT the default
        language locale. The default language locale will be kept as-is.
        """

        xmldoc = minidom.parseString(xml_str)

        # Remove existing locales. Make sure we don't remove the default one (all_ALL) if we don't have to.
        locales = xmldoc.getElementsByTagName("Locale")
        for loc in locales:
            # Check whether it is the DEFAULT locale.
            if respect_default:
                if "lang" not in loc.attributes.keys() and "country" not in loc.attributes.keys():
                    raise

            parent = loc.parentNode
            parent.removeChild(loc)


    # TODO: Consider whether non-specified lang and country should default to "all".
    # TODO: Add error detection. XMLs may fail to load, they may not contain the expected tags, etc.
    def update_bundles(self, xml_str):
        """
        update_bundles(xml_str)

        Updates the bundles in a XML gadget spec using the Manager's bundles.
        """
        xmldoc = minidom.parseString(xml_str)

        # Remove existing locales
        locales = xmldoc.getElementsByTagName("Locale")
        for loc in locales:
            parent = loc.parentNode
            parent.removeChild(loc)

        # Add the locales to ModulePrefs
        module_prefs = xmldoc.getElementsByTagName("ModulePrefs")[0]
        for name, bundle in self._bundles.items():
            locale = xmldoc.createElement("Locale")
            if bundle.lang == "":
                bundle.lang = "all"
            if bundle.country == "":
                bundle.lang = "all"

            base_url = self._base_publish_url
            filename = bundle.lang + "_" + bundle.country + ".xml"
            full_filename = base_url + "/" + filename

            locale.setAttribute("messages", full_filename)
            locale.setAttribute("lang", bundle.lang)
            locale.setAttribute("country", bundle.country)

            locale.appendChild(xmldoc.createTextNode(""))
            module_prefs.appendChild(locale)

        return xmldoc.toprettyxml()


class Bundle(object):
    """
    Represents a Bundle. A bundle is a set of messages for a specific language, group and country.
    The default language, group and country is ANY.
    By convention, language is in lowercase while country is in uppercase.
    Group is not yet defined.
    """

    def __init__(self, country, lang, group=""):
        self.country = country
        self.lang = lang
        self.group = group

        self._msgs = {
            # identifier : translation
        }

    def add_msg(self, word, translation):
        """
        Adds a translation to the dictionary.
        """
        self._msgs[word] = translation

    def remove_msg(self, word):
        """
        Removes a translation from the dictionary.
        """
        del self._msgs[word]

    def to_jsonable(self):
        """
        Converts the Bundle to a JSON-able dictionary.
        """
        bundle_data = {"country": self.country, "lang": self.lang, "group": self.group, "messages": self._msgs}
        return bundle_data

    def to_json(self):
        """
        Converts the Bundle to JSON.
        """
        bundle_data = {"country": self.country, "lang": self.lang, "group": self.group, "messages": self._msgs}
        json_str = json.dumps(bundle_data)
        return json_str

    @staticmethod
    def from_json(json_str):
        """
        Builds a fully new Bundle from JSON.
        """
        bundle_data = json.loads(json_str)
        bundle = Bundle(bundle_data["country"], bundle_data["lang"], bundle_data["group"])
        bundle._msgs = bundle_data["messages"]
        return bundle

    @staticmethod
    def from_xml(xml_str, country, lang, group=""):
        """
        Creates a new Bundle from XML.
        """
        bundle = Bundle(country, lang, group)
        xmldoc = minidom.parseString(xml_str)
        itemlist = xmldoc.getElementsByTagName("msg")
        for elem in itemlist:
            bundle.add_msg(elem.attributes["name"].nodeValue, elem.firstChild.nodeValue.strip())
        return bundle

    def to_xml(self):
        """
        Converts the Bundle to XML.
        """
        out = StringIO.StringIO()
        out.write('<messagebundle>\n')
        for (name, msg) in self._msgs.items():
            out.write('    <msg name="%s">%s</msg>\n' % (name, msg))
        out.write('</messagebundle>\n')
        return out.getvalue()


@translate_blueprint.route('/app/<appid>/app.xml')
def app_xml(appid):
    app = get_app(appid)
    # TODO: Verify that the app is a "translate" app.
    data = json.loads(app.data)
    spec_file = data["spec"]

    bm = BundleManager(spec_file)
    bm._load_spec(spec_file)
    output_xml = bm.update_bundles(bm.original_xml)

    response = make_response(output_xml)
    response.mimetype = "application/xml"
    return response


@translate_blueprint.route('/app/<appid>/<langfile>.xml')
def app_langfile(appid, langfile):
    app = get_app(appid)

    # TODO: Figure out how to handle 404 errors here. (Check whether it could crash a gadget etc).
    # Try to load the bundle with that lang.
    bundles = app.data["bundles"]
    if langfile not in bundles:
        dbg_info = str(bundles.keys())
        return "Could not find such language. Available keys are: " + dbg_info, 404

    # TODO: Add from_jsonable
    bundle = Bundle.from_json(json.dumps(bundles[langfile]))

    output_xml = bundle.to_xml()

    response = make_response(output_xml)
    response.mimetype = "application/xml"
    return response


@translate_blueprint.route('/backend', methods=['GET', 'POST'])
def backend():
    testxml = """
    <messagebundle>
        <msg name="hello_world">
            Hello World.
        </msg>
        <msg name="color">Color</msg>
        <msg name="red">Red</msg>
        <msg name="green">Green</msg>
        <msg name="blue">Blue</msg>
        <msg name="gray">Gray</msg>
        <msg name="purple">Purple</msg>
        <msg name="black">Black</msg>
    </messagebundle>
    """

    bundle = Bundle.from_xml(testxml, "es", "ES")
    jsonstr = bundle.to_json()
    bundle = Bundle.from_json(jsonstr)
    xmlstr = bundle.to_xml()

    return Markup.escape(xmlstr)


@translate_blueprint.route('/backendt', methods=['GET', 'POST'])
def backendt():
    bm = BundleManager()
    bm._load_spec("https://dl.dropboxusercontent.com/u/6424137/i18n.xml")

    bundles = ""
    for bundle in bm._bundles.values():
        bundles += bundle.to_json()
    return Markup.escape(bundles)


@translate_blueprint.route('/backend2', methods=['GET', 'POST'])
def backendt():
    bm = BundleManager()
    url = "https://dl.dropboxusercontent.com/u/6424137/i18n.xml"
    bm._load_spec(url)

    bundles = "";
    for bundle in bm._bundles.values():
        bundles += bundle.to_json()

    xml = bm._read_url(url)

    result = bm.update_bundles(xml)
    return Markup.escape(result)

