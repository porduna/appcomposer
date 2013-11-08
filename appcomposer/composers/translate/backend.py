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
NOTE ABOUT THE GENERAL WORKFLOW DESIGN:
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


 NOTE ABOUT THE REQUIREMENTS ON THE APP TO BE TRANSLATED:
 The App to be translated should be already internationalized and should contain at least a reference to one Bundle,
 the Default language Bundle. This is a Locale node on the spec, with NO lang attribute and NO country attribute.
 (If this entry does not exist the App can't be translated).


 FILE NAMING CONVENTIONS:
 The convention we will try to use here is the following:

 Example: ca_ES.xml (for language files)

 ca would be the language.
 ES would be the country.

 If any is not set, then it will be replaced with "all", in the right case. For instance,
 if lang is not specified it will be all_ES. Or if the country isn't, es_ALL.

 The default language is always all_ALL and should always be present.



 """

# TODO: Ensure throughout this class that bundle.lang and bundle.country NEVER contain empty strings or None values.
# If appropriate they should contain "all".


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


class UnexpectedTranslateDataException(Exception):
    """
    Exception thrown when the format of the internally stored translate data does not seem
    to be as expected.
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
        self.original_spec_file = original_gadget_spec

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


    def _retrieve_url(self, url):
        """
        Simply retrieves a specified URL (Synchronously).
        @param url: URL to retrieve.
        @return: Contents of the URL.
        """
        handle = urllib.urlopen(url)
        contents = handle.read()
        return contents

    def load_full_spec(self, url):
        """
        Fully loads the specified Gadget Spec.
        This is meant to be used when first loading a new App, so that all existing languages are taken into account.
        @param url:  URL to the XML Gadget Spec.
        @return: Nothing. The bundles are internally stored once parsed.
        """
        # Store the specified URL as the gadget spec.
        self.original_spec_file = url

        # Retrieve the original spec. This may take a while.
        xml_str = self._retrieve_url(url)

        self.original_xml = xml_str

        # Extract the locales from the XML.
        # TODO: Revise this method.
        locales = self._extract_locales_from_xml(xml_str)

        for lang, country, bundle_url in locales:
            bundle_xml = self._retrieve_url(bundle_url)
            bundle = Bundle.from_xml(bundle_xml, country, lang)
            name = self.generate_standard_name(country, lang)
            self._bundles[name] = bundle


    def _load_spec(self, url):
        """
        Fully loads the specified gadget spec.
        @param url: URL to the XML Gadget Spec.
        @return: Nothing. The bundles are internally stored once parsed.
        """

        # Store the specified URL as the gadget spec.
        self.original_spec_file = url

        xml_str = self._retrieve_url(url)
        self.original_xml = xml_str
        locales = self._extract_locales_from_xml(xml_str)
        for loc in locales:
            bundle_xml = self._retrieve_url(loc[2])
            bundle = Bundle.from_xml(bundle_xml, loc[0], loc[1])
            name = self.generate_standard_name(loc[0], loc[1])
            self._bundles[name] = bundle

    def to_json(self):
        """
        Exports everything to JSON.
        """
        data = {
            "spec": self.original_spec_file,
            "bundles": {}
        }
        for name, bundle in self._bundles.items():
            data["bundles"][name] = bundle.to_jsonable()
        return json.dumps(data)

    def from_json(self, json_str):
        """
        Loads the specified JSON into the BundleManager.
        @param json: JSON string to load.
        @return: Nothing
        """
        appdata = json.loads(json_str)
        bundles = appdata["bundles"]
        for name, bundledata in bundles.items():
            # TODO: Kludgey and inefficient. Fix/refactor this.
            bundlejs = json.dumps(bundledata)
            bundle = Bundle.from_json(bundlejs)
            self._bundles[name] = bundle
        return

    def generate_standard_name(self, lang, country):
        """
        From the lang and country information, it generates a standard name for the file.
        Standard names follow the convention: "ca_ES".
        Case is important.
        Also, if either of them is empty or None, then it will be replaced with "all" in the appropriate case.
        The XML file termination is NOT appended.
        """
        if lang is None or lang == "":
            lang = "all"
        if country is None or country == "":
            country = "ALL"
        return "%s_%s" % (lang.lower(), country.upper())

    def _extract_locales_from_xml(self, xml_str):
        """
        _extract_locales_from_xml(xml_str)
        Extracts the Locale nodes info from an xml_str (a gadget spec).
        @param xml_str: String containing the XML of a locale file.
        @return: A list of tuples: (lang, country, message_file)
        @note: If the lang or country don't exist, it replaces them with "all" or "ALL" respectively.
        """
        locales = []
        xmldoc = minidom.parseString(xml_str)
        itemlist = xmldoc.getElementsByTagName("Locale")
        for elem in itemlist:
            messages_file = elem.attributes["messages"].nodeValue

            try:
                lang = elem.attributes["lang"].nodeValue
            except KeyError:
                lang = "all"

            try:
                country = elem.attributes["country"].nodeValue
            except KeyError:
                country = "ALL"

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
        default_locale_found = False
        for loc in locales:
            # Check whether it is the DEFAULT locale.
            if respect_default:
                # This is indeed the default node. Go on to next iteration without removing the locale.
                if "lang" not in loc.attributes.keys() and "country" not in loc.attributes.keys():
                    default_locale_found = True
                    continue

            # Remove the node.
            parent = loc.parentNode
            parent.removeChild(loc)

        # If we are supposed to respect the default, ensure that we actually found it.
        if respect_default:
            if not default_locale_found:
                raise NoDefaultLanguageException("The Gadget Spec does not seem to have a link to a default Locale."
                                                 "It is probably not ready to be translated.")

        # We have now removed the Locale nodes. Inject the new ones to the ModulePrefs node.
        module_prefs = xmldoc.getElementsByTagName("ModulePrefs")[0]
        for name, bundle in self._bundles.items():

            # Just in case we need to respect the default bundle.
            if respect_default:
                if name == "all_ALL":  # The default bundle MUST always be named thus.
                    # This is the default Locale. We have left the original one on the ModulePrefs node, so
                    # we don't need to append it. Go on to next Locale.
                    continue

            locale = xmldoc.createElement("Locale")

            # Build our locales to inject. We modify the case to respect the standard. It shouldn't be necessary
            # but we do it nonetheless just in case other classes fail to respect it.
            filename = bundle.lang.lower() + "_" + bundle.country.upper() + ".xml"
            full_filename = host_url + "/" + filename

            locale.setAttribute("messages", full_filename)
            if bundle.lang != "all":
                locale.setAttribute("lang", bundle.lang)
            if bundle.country != "ALL":
                locale.setAttribute("country", bundle.country)

            # Inject the node we have just created.
            locale.appendChild(xmldoc.createTextNode(""))
            module_prefs.appendChild(locale)

        return xmldoc.toprettyxml()


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
    """
    app_xml(appid)

    Provided for end-users. This is the function that provides hosting for the
    gadget specs for a specified App. The gadget specs are actually dynamically
    generated, as every time a request is made the original XML is obtained and
    modified.

    @param appid: Identifier of the App.
    @return: XML of the modified Gadget Spec with the Locales injected, or an HTTP error code
    if an error occurs.
    """
    app = get_app(appid)

    if app is None:
        return "Error 404: App doesn't exist", 404

    # TODO: Verify that the app is a "translate" app.

    appdata = json.loads(app.data)
    spec_file = appdata["spec"]

    bm = BundleManager(spec_file)
    bm.from_json(app.data)

    xmlspec = bm._retrieve_url(spec_file)

    output_xml = bm._inject_locales_into_spec("localhost", xmlspec, True)

    response = make_response(output_xml)
    response.mimetype = "application/xml"
    return response


@translate_blueprint.route('/app/<appid>/i18n/<langfile>')
def app_langfile(appid, langfile):
    """
    app_langfile(appid, langfile)

    Provided for end-users. This is the function that provides hosting for the
    langfiles for a specified App. The langfiles are actually dynamically
    generated (the information is extracted from the Translate-specific information).

    @param appid: Appid of the App whose langfile to generate.
    @param langfile: Name of the langfile. Must follow the standard: ca_ES
    @return: Google OpenSocial compatible XML, or an HTTP error code
    if an error occurs.
    """
    app = get_app(appid)

    if app is None:
        return "Error 404: App doesn't exist", 404

    # Parse the appdata
    appdata = json.loads(app.data)

    bundles = appdata["bundles"]
    if langfile not in bundles:
        dbg_info = str(bundles.keys())
        return "Error 404: Could not find such language for the specified app. Available keys are: " + dbg_info, 404

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

    xml = bm._retrieve_url(url)

    result = bm.update_bundles(xml)
    return Markup.escape(result)

