import json
import urllib
from markupsafe import Markup
from appcomposer.composers.translate import translate_blueprint
from xml.dom import minidom
import StringIO


class BundleManager(object):
    def __init__(self, base_publish_url=""):
        self._bundles = {}
        self._base_publish_url = base_publish_url

    def _read_url(self, url):
        """
        Simply retrieves a specified URL (Synchronously).
        @param url: URL to retrieve.
        @return: Contents of the URL.
        """
        handle = urllib.urlopen(url)
        contents = handle.read()
        return contents

    def load_spec(self, url):
        """
        Fully loads the specified gadget spec.
        @param url: URL to the XML Gadget Spec.
        @return: Nothing. The bundles are internally stored once parsed.
        """
        xml_str = self._read_url(url)
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
            "bundles": {}
        }
        for name, bundle in self._bundles.items():
            data["bundles"][name] = bundle.to_jsonable()
        return json.dumps(data)


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
    def __init__(self, country, lang, group=""):
        self.country = country
        self.lang = lang
        self.group = group

        self._msgs = {
            # identifier : translation
        }

    def add_msg(self, word, translation):
        self._msgs[word] = translation

    def remove_msg(self, word):
        del self._msgs[word]

    def to_jsonable(self):
        bundle_data = {"country": self.country, "lang": self.lang, "group": self.group, "messages": self._msgs}
        return bundle_data

    def to_json(self):
        bundle_data = {"country": self.country, "lang": self.lang, "group": self.group, "messages": self._msgs}
        json_str = json.dumps(bundle_data)
        return json_str

    @staticmethod
    def from_json(json_str):
        bundle_data = json.loads(json_str)
        bundle = Bundle(bundle_data["country"], bundle_data["lang"], bundle_data["group"])
        bundle._msgs = bundle_data["messages"]
        return bundle

    @staticmethod
    def from_xml(xml_str, country, lang, group=""):
        bundle = Bundle(country, lang, group)
        xmldoc = minidom.parseString(xml_str)
        itemlist = xmldoc.getElementsByTagName("msg")
        for elem in itemlist:
            bundle.add_msg(elem.attributes["name"].nodeValue, elem.firstChild.nodeValue.strip())
        return bundle

    def to_xml(self):
        out = StringIO.StringIO()
        out.write('<messagebundle>\n')
        for (name, msg) in self._msgs.items():
            out.write('    <msg name="%s">%s</msg>\n' % (name, msg))
        out.write('</messagebundle>\n')
        return out.getvalue()


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
    bm.load_spec("https://dl.dropboxusercontent.com/u/6424137/i18n.xml")

    bundles = ""
    for bundle in bm._bundles.values():
        bundles += bundle.to_json()
    return Markup.escape(bundles)


@translate_blueprint.route('/backend2', methods=['GET', 'POST'])
def backendt():
    bm = BundleManager()
    url = "https://dl.dropboxusercontent.com/u/6424137/i18n.xml"
    bm.load_spec(url)

    bundles = "";
    for bundle in bm._bundles.values():
        bundles += bundle.to_json()

    xml = bm._read_url(url)

    result = bm.update_bundles(xml)
    return Markup.escape(result)

