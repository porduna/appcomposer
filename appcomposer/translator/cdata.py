import xml.etree.ElementTree as ET

# Code from: 
# http://stackoverflow.com/questions/1091945/what-characters-do-i-need-to-escape-in-xml-documents
def CDATA(text=None):
    element = ET.Element('![CDATA[')
    element.text = text
    return element

ET._original_serialize_xml = ET._serialize_xml
if ET._serialize_xml.func_code.co_argcount == 5:
    # Python 2
    def _serialize_xml(write, elem, encoding, qnames, namespaces):
        if elem.tag == '![CDATA[':
            write((u"<%s%s]]>" % (elem.tag, elem.text)).encode(encoding))
            return
        return ET._original_serialize_xml(
            write, elem, encoding, qnames, namespaces)
else:
    # Python 3
    def _serialize_xml(write, elem, qnames, namespaces):
        if elem.tag == '![CDATA[':
            write("<%s%s]]>" % (
                    elem.tag, elem.text))
            return
        return ET._original_serialize_xml(
            write, elem, qnames, namespaces)

ET._serialize_xml = ET._serialize['xml'] = _serialize_xml

