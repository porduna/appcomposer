import json
import urllib
from markupsafe import Markup
from appcomposer.composers.translate import translate_blueprint
from xml.dom import minidom
import StringIO


class BundleManager(object):
    def __init__(self):
        self._bundles = {}

    def _read_url(self, url):
        handle = urllib.urlopen(url)
        contents = handle.read()
        return contents

    def load_spec(self, url):
        xml_str = self._read_url(url)
        locales = self._extract_locales(xml_str)
        for loc in locales:
            bundle_xml = self._read_url(loc[2])
            bundle = Bundle.from_xml(bundle_xml, loc[0], loc[1])
            name = self.get_name(loc[0], loc[1])
            self._bundles[name] = bundle

    def get_name(self, lang, country):
        if lang is None or lang == "":
            lang = "ANY"
        if country is None or country == "":
            country = "ANY"
        return "%s_%s" % (lang, country)

    def _extract_locales(self, xml_str):
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

    bundles = "";
    for bundle in bm._bundles.values():
        bundles += bundle.to_json()
    return Markup.escape(bundles)

