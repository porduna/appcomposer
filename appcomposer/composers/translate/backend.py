import json
from appcomposer.composers.translate import translate_blueprint
from xml.dom import minidom
import StringIO


class Bundle(object):
    def __init__(self, country, lang, group):
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
    def from_xml(xml_str, country, lang, group):
        bundle = Bundle(country, lang, group)
        xmldoc = minidom.parseString(xml_str)
        itemlist = xmldoc.getElementsByTagName("msg")
        for elem in itemlist:
            bundle.add_msg(elem.attributes["name"], elem.firstChild.nodeValue)
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
    return "Backend"
