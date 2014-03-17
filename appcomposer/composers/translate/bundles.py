import StringIO
import json
import os
import urllib
import urlparse
from xml.dom import minidom
from babel import Locale, UnknownLocaleError
from flask import url_for


class BundleManager(object):
    """
    To manage the set of bundles for an App, and to provide common functionality.
    """

    def __init__(self, original_gadget_spec=None):
        """
        Builds the BundleManager.
        Note that there are additional CTORs available for specific use-cases, which start with create_*.
        @param original_gadget_spec: URL of the original XML of the App.
        """
        self._bundles = {}

        # Points to the original gadget spec XML.
        self.original_spec_file = original_gadget_spec

    def get_gadget_spec(self):
        """
        Gets the path to the XML file that originally describes the app.
        That is, the app Spec file.
        @return:
        """
        return self.original_spec_file

    @staticmethod
    def create_new_app(app_spec_url, progress_callback=None):
        """
        Handles the creation of a completely new App from a standard OpenSocial XML specification.
        This operation needs to request the external XML and in some cases external XMLs referred by it.
        As such, it can take a while to complete, and there are potential security issues.

        @param app_spec_url: URL of the XML to use to construct the App.
        @param progress_callback: Optional callback to receive progress updates.
        """
        bm = BundleManager()
        bm.load_full_spec(app_spec_url, progress_callback)
        return bm

    @staticmethod
    def create_from_existing_app(app_data):
        """
        Acts as a CTOR. Creates a BundleManager for managing an App that exists already.

        @param app_data: JSON string, or JSON-able dictionary containing the Translate App's data.
        @return: The new BundleManager, with the specified App's data loaded.
        """
        if type(app_data) is str or type(app_data) is unicode:
            app_data = json.loads(app_data)

        spec_file = app_data["spec"]
        bm = BundleManager(spec_file)

        bm.merge_json(app_data)

        return bm

    @staticmethod
    def get_locale_info_from_code(code):
        """
        Retrieves the lang, country and group from a full or partial locale code.
        @param code: Locale code. It can be a full code (ca_ES_ALL) or partial code (ca_ES).
        @return: (lang, country, group) or (lang, country), depending if it's full or partial.
        """
        splits = code.split("_")

        # If our code is only "ca_ES" style (doesn't include group).
        if len(splits) == 2:
            lang, country = splits
            return lang, country

        # If we have 3 splits then it is probably "ca_ES_ALL" style (includes group).
        elif len(splits) == 3:
            lang, country, group = splits
            return lang, country, group

        # Unknown number of splits. Throw an exception, it is not a recognized code.
        else:
            raise UnrecognizedLocaleCodeException("The locale code can't be recognized: " + code)

    @staticmethod
    def get_locale_english_name(lang, country):
        """
        Retrieves a string representation of a Locale.
        @param lang: Lang code.
        @param country: Country code.
        @return: String representation for the locale.
        """
        try:
            if country.upper() == 'ALL':
                country = ""
            return Locale(lang, country).english_name
        except UnknownLocaleError:
            return Locale("en", "US").languages.get(lang)

    @staticmethod
    def fullcode_to_partialcode(code):
        """
        Converts a full_code to a partial_code (with no group). That is, a code such as ca_ES_ALL to ca_ES.
        @param code: Fully fledged code, such as ca_ES_ALL.
        @return: Partial code, such as ca_ES.
        """
        lang, country, group = BundleManager.get_locale_info_from_code(code)
        return "%s_%s" % (lang.lower(), country.upper())

    @staticmethod
    def partialcode_to_fullcode(code, group):
        """
        Converts a partial_code to a full_code, adding group information. That is, a code such as ca_ES becomes
        a code such as ca_ES_ALL.
        @param code: Full code, such as ca_ES_ALL
        @return: Partial code, such as ca_ES.
        """
        lang, country = BundleManager.get_locale_info_from_code(code)
        return "%s_%s_%s" % (lang.lower(), country.upper(), group.upper())


    # TODO: Add support for non-standard xml specs. For instance, if the lang contains "es_ES" we should probably try
    # to fail gracefully. (Or actually to ignore the pack).
    # TODO: Careful when it fails so that no partially-created App remains.
    def get_locales_list(self):
        """
        get_locales_list()
        Retrieves a list containing dictionaries of the locales that are currently loaded in the manager.
        @return: List of dictionaries with the following information: {code, lang, country, group}
        """
        locales = []
        for key in self._bundles.keys():
            lang, country, group = key.split("_")
            loc = {"code": key, "pcode": BundleManager.fullcode_to_partialcode(key), "lang": lang, "country": country,
                   "group": group,
                   "repr": BundleManager.get_locale_english_name(lang, country)}
            locales.append(loc)
        return locales

    @staticmethod
    def _retrieve_url(url):
        """
        Simply retrieves a specified URL (Synchronously).
        @param url: URL to retrieve. Should be absolute, not relative.
        @return: Contents of the URL.
        """
        handle = urllib.urlopen(url)
        contents = handle.read()
        return contents

    def _to_absolute_url(self, url):
        """
        Converts the provided URL into absolute if it isn't already.
        It uses the xml spec as base.
        """
        # Check if the url is already absolute.
        is_absolute = bool(urlparse.urlparse(url).netloc)
        if is_absolute:
            return url

        # Extract the base.
        base = os.path.dirname(self.original_spec_file)

        # Append the file to the base.
        return base + os.sep + url

    def load_full_spec(self, url, progress_callback=None):
        """
        Fully loads the specified Gadget Spec.
        This is meant to be used when first loading a new App, so that all existing languages are taken into account.
        Google default i18n mechanism doesn't support groups. Hence, all "imported" bundles will be created for the
        group "ALL", which is the default one for us.
        @param url:  URL to the XML Gadget Spec.
        @param progress_callback: This function may take a long time. If other than None, will receive notifications when progress is made.
        The callback should be a function with three arguments: function callback(tasks_done, total_tasks, update_message). Total tasks may be None if they
        are not known.
        @return: Nothing. The bundles are internally stored once parsed.
        """
        # Store the specified URL as the gadget spec.
        self.original_spec_file = url

        # Retrieve the original spec. This may take a while.
        xml_str = self._retrieve_url(url)

        # For progress reporting.
        tasks_done = 0
        total_tasks = None

        # Extract the locales from the XML.
        locales = self._extract_locales_from_xml(xml_str)

        tasks_done += 1
        update_message = "Retrieved base XML specification file"
        if progress_callback is not None:
            progress_callback(tasks_done, total_tasks, update_message)

        total_tasks = len(locales)+1
        for lang, country, bundle_url in locales:
            try:
                # TODO: Warning. The provided URL in an xml can be relative (or can it not?).
                bundle_url = self._to_absolute_url(bundle_url)  # Will convert it if it isn't already.
                bundle_xml = self._retrieve_url(bundle_url)
                bundle = Bundle.from_xml(bundle_xml, lang, country, "ALL")
                name = Bundle.get_standard_code_string(lang, country, "ALL")
                self._bundles[name] = bundle

                tasks_done += 1  # For progress reporting.
                update_message = "Extracted bundle for " + name
                if progress_callback is not None:
                    progress_callback(tasks_done, total_tasks, update_message)
            except:
                # TODO: For now, we do not really handle errors, we simply ignore those locales which cause exceptions.
                # In the future, we should probably analyze which kind of exceptions can occur, and decide what
                # we must do in each case. For instance, sometimes we might wanna ignore the Bundle but sometimes we
                # might wanna notify the user, etc. Also, there may be some cases of invalid bundles in which no
                # exception occurs but which are somewhat invalid nonetheless.
                pass

    def to_json(self):
        """
        Exports everything to JSON. It includes both the JSON for the bundles, and a spec attribute, which
        links to the original XML file (it will be requested everytime).
        """
        data = {
            "spec": self.original_spec_file,
            "bundles": {}
        }
        for name, bundle in self._bundles.items():
            data["bundles"][name] = bundle.to_jsonable()
        return json.dumps(data)

    def load_from_json(self, json_str):
        """
        Loads the specified JSON into the BundleManager. It just loads from the JSON.
        It doesn't carry out any external request. Whole bundles may be replaced. If you don't want
        bundles to be fully replaced, use merge_json instead.
        @param json_str: JSON string to load.
        @return: Nothing
        """
        appdata = json.loads(json_str)
        bundles = appdata["bundles"]
        for name, bundledata in bundles.items():
            bundle = Bundle.from_jsonable(bundledata)
            self._bundles[name] = bundle

        self.original_spec_file = appdata["spec"]
        return

    def merge_json(self, json_data):
        """
        Merges the specified json into the BundleManager. It will simply load from the JSON,
        replacing existing entries in bundles as needed.
        @param json_data: JSON string to load, or JSON-able data structure.
        @return: Nothing.
        """
        if type(json_data) == str or type(json_data) == unicode:
            appdata = json.loads(json_data)
        else:
            appdata = json_data
        bundles = appdata["bundles"]
        for name, bundledata in bundles.items():
            bundle = Bundle.from_jsonable(bundledata)
            # If the bundle doesn't exist we just store it.
            # If it does exist we need to do a real merge.
            if name in self._bundles:
                basebundle = self._bundles[name]
                self._bundles[name] = Bundle.merge(basebundle, bundle)
            else:
                self._bundles[name] = bundle

    @staticmethod
    def _extract_locales_from_xml(xml_str):
        """
        _extract_locales_from_xml(xml_str)
        Extracts the Locale nodes info from an xml_str (a gadget spec).
        @param xml_str: String containing the XML of a locale file.
        @return: A list of tuples: (lang, country, message_file)
        @note: If the lang or country don't exist, it replaces them with "all" or "ALL" respectively.
        @note: The XML format is specified by Google and does not support the concept of "groups".
        """
        locales = []

        try:
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
        except:
            raise InvalidXMLFileException("Could not parse XML file")

        return locales

    def _inject_locales_into_spec(self, appid, xml_str, respect_default=True, group=None):
        """
        _inject_locales_into_spec(appid, xml_str)

        Generates a new Gadget Spec from a provided Gadget Spec, replacing every original Locale with links
        to custom Locales, with application identifier appid.

        Optionally, it can avoid modifying the default translation.
        This is done so that if the original author updates the translation, this takes immediate effect
        into the translated versions of the App.

        @param appid: Application identifier of the current application.

        @param xml_str: String containing the XML of the original Gadget Spec.

        @param respect_default: If false, every Locale will be removed and replaced with custom links to the
        language, using the appid as application identifier. If true, the same will be done to every Locale, EXCEPT the
        default language locale. The default language locale will be kept as-is.

        @param group: If set, then the locales will be filtered by group.
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
                if name == "all_ALL_ALL":  # The default bundle MUST always be named thus.
                    # This is the default Locale. We have left the original one on the ModulePrefs node, so
                    # we don't need to append it. Go on to next Locale.
                    continue

            # If we need to filter by group, then we will do so.
            if group is not None:
                if bundle.group != group:
                    continue

            locale = xmldoc.createElement("Locale")

            # Build our locales to inject. We modify the case to respect the standard. It shouldn't be necessary
            # but we do it nonetheless just in case other classes fail to respect it.
            full_filename = url_for('.app_langfile', appid=appid,
                                    langfile=Bundle.get_standard_code_string(bundle.lang, bundle.country,
                                                                             bundle.group), _external=True)

            locale.setAttribute("messages", full_filename)
            if bundle.lang != "all":
                locale.setAttribute("lang", bundle.lang)
            if bundle.country != "ALL":
                locale.setAttribute("country", bundle.country)

            # Inject the node we have just created.
            locale.appendChild(xmldoc.createTextNode(""))
            module_prefs.appendChild(locale)

        return xmldoc.toprettyxml()

    def get_bundle(self, bundle_code):
        """
        get_bundle(bundle_code)

        Retrieves a bundle by its code.

        @param bundle_code: Name for the bundle. Example: ca_ES_ALL or all_ALL_ALL.
        @return: The bundle for the given name. None if the Bundle doesn't exist in the manager.
        """
        return self._bundles.get(bundle_code)

    def add_bundle(self, full_code, bundle):
        """
        Adds the specified Bundle to the BundleManager.
        @param full_code: Full code of the bundle, in ca_ES_ALL format (must include lang, country and group).
        @param bundle: The Bundle to add.
        @return: Nothing
        """
        if full_code in self._bundles:
            raise BundleExistsAlreadyException()
        self._bundles[full_code] = bundle

    def do_render_app_xml(self, appid, group=None):
        """
        Renders the Gadget Spec XML for the specified App.
        This method assumes that the BundleManager has already been loaded properly
        with the App's translations, and that the spec file is pointed to the right place.

        @param appid String with the unique ID of the application whose Bundles to generate. This is
        required because some URLs included in the generated XML include it.
        @param group Optional. If set, the bundles to print will be filtered by group.
        """
        xmlspec = self._retrieve_url(self.original_spec_file)
        output_xml = self._inject_locales_into_spec(appid, xmlspec, True, group)
        return output_xml

    def merge_bundle(self, base_bundle_code, proposed_bundle):
        """
        Merges two bundles. Messages in the proposed_bundle will replace those messages
        with the same name in the base bundle.

        @param base_bundle_code: The code of the bundle to use as base. If it exists, it
        will be found within this manager. Otherwise the merge will be trivial, because
        a new bundle for that code will simply be created with the proposed_bundle's contents.

        @param proposed_bundle: The proposed bundle. This should be a Bundle object.
        """
        base_bundle = self.get_bundle(base_bundle_code)

        if base_bundle is None:
            # The bundle doesn't exist, so no actual merge is needed.
            self._bundles[base_bundle_code] = proposed_bundle
        else:
            # Merge the proposed Bundle with our Bundle.
            merged_bundle = Bundle.merge(base_bundle, proposed_bundle)
            self._bundles[base_bundle_code] = merged_bundle

    def merge_language(self, language_partial_code, from_app):
        """
        Merges a full language within from_app into the BundleManager.

        @param language_partial_code: A partial code identifying the language to merge,
        such as ca_ES. Every bundle for that language (all groups) will be merged.

        @note: Any value which exists already in the calling BundleManager will be replaced
        if a value with the same name is in from_app and satisfies the merging conditions.
        """
        from_bm = BundleManager.create_from_existing_app(from_app.data)

        # Find those bundles we must merge (all groups for the specified language).
        for bundle_name in from_bm._bundles.keys():
            partialcode = BundleManager.fullcode_to_partialcode(bundle_name)
            if partialcode == language_partial_code:
                # We found a bundle we must merge.
                print "MERGING: " + bundle_name
                proposed_bundle = from_bm.get_bundle(bundle_name)
                self.merge_bundle(bundle_name, proposed_bundle)
            else:
                print "NOT MERGING: " + bundle_name


class Bundle(object):
    """
    Represents a Bundle. A bundle is a set of messages for a specific language, group and country.
    The default language, group and country is ANY.
    By convention, language is in lowercase while country is in uppercase.
    Group is uppercase too.
    """

    def __init__(self, lang, country, group="ALL"):
        self.country = country
        self.lang = lang
        self.group = group

        self._msgs = {
            # identifier : translation
        }

    @staticmethod
    def merge(base_bundle, merging_bundle, ignore_empty=True):
        """
        Merges the merging_bundle into tbe base_bundle. The resulting bundle will contain the elements from both
        bundles. Those elements in the base_bundle which have been changed in the merging_bundle will be replaced
        by those in the merging_bundle. The (lang, country, group) of the resulting bundle will be the same as
        the base's.

        @param base_bundle: The base bundle. Elements which are different in the merging_bundle will be replaced
        in the resulting bundle.
        @param merging_bundle: The bundle to merge into the base_bundle. The resulting bundle will contain every
        element in the merging_bundle as it is.
        @param ignore_empty: If ignore_empty is set to True (the default) then if the merging_bundle contains
        an element that is None or empty, that element will be ignored, and that element won't be replaced
        in the base_bundle.
        @return: A resulting bundle which is the merge of the merging_bundle into the base_bundle.
        """
        rb = Bundle(base_bundle.lang, base_bundle.country, base_bundle.group)

        # Copy the base_bundle into rb
        for ident, msg in base_bundle._msgs.items():
            rb._msgs[ident] = msg

        # Copy the merging_bundle items over the rb
        for ident, msg in merging_bundle._msgs.items():
            if not ignore_empty or (msg is not None and len(msg) > 0):
                rb._msgs[ident] = msg

        return rb

    @staticmethod
    def get_standard_code_string(lang, country, group):
        """
        From the lang, country and group information, it generates a standard name for the file.
        Standard names follow the convention: "ca_ES_ALL".
        Case is important.
        Also, if either of them is empty or None, then it will be replaced with "all" in the appropriate case.
        The XML file termination is NOT appended.
        """
        if lang is None or lang == "":
            lang = "all"
        if country is None or country == "":
            country = "ALL"
        if group is None or group == "":
            group = "ALL"
        return "%s_%s_%s" % (lang.lower(), country.upper(), group.upper())

    def get_msgs(self):
        """
        Retrieves the whole dictionary of translations for the Bundle.
        @return: Dictionary containing the translation. WARNING: Do not modify the dictionary.
        """
        return self._msgs

    def get_msg(self, identifier):
        """
        Retrieves the translation of a specific message.
        @param identifier: Identifier of the message to retrieve.
        @return: Message linked to the identifier, or None if it doesn't exist.
        """
        return self._msgs.get(identifier)

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
    def from_jsonable(bundle_data):
        """
        Builds a fully new Bundle from JSONable data. That is, a dictionary containing no references etc.
        """
        bundle = Bundle(bundle_data["lang"], bundle_data["country"], bundle_data["group"])
        bundle._msgs = bundle_data["messages"]
        return bundle

    @staticmethod
    def from_json(json_str):
        """
        Builds a fully new Bundle from JSON.
        """
        bundle_data = json.loads(json_str)
        return Bundle.from_jsonable(bundle_data)

    @staticmethod
    def from_xml(xml_str, lang, country, group="ALL"):
        """
        Creates a new Bundle from XML.
        """
        try:
            bundle = Bundle(lang, country, group)
            xmldoc = minidom.parseString(xml_str)
            itemlist = xmldoc.getElementsByTagName("msg")
            for elem in itemlist:
                bundle.add_msg(elem.attributes["name"].nodeValue, elem.firstChild.nodeValue.strip())
        except:
            raise InvalidXMLFileException("Could not load an XML translation")
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

    @classmethod
    def from_messages(cls, proposal_data, bundle_code):
        """
        Builds a new Bundle from a dictionary containing the messages, and a full bundle_code.
        @param proposal_data Dictionary with the messages.
        @param bundle_code Full code in the CA_ES_ALL format.
        """
        lang, country, group = bundle_code.split("_")
        bundle = Bundle(lang, country, group)
        bundle._msgs = proposal_data
        return bundle


class UnrecognizedLocaleCodeException(Exception):
    """
    Exception thrown when the format of a locale code does not seem to be
    as expected.
    """

    def __init__(self, message=None):
        self.message = message


class InvalidXMLFileException(Exception):
    """
    Exception to be thrown when the XML spec of the App can't be parsed, most likely because
    it contains invalid XML.
    """

    def __init__(self, message=None):
        self.message = message


class NoDefaultLanguageException(Exception):
    """
    Exception to be thrown when an App specified to be translated does not have a default translation.
    (And hence it is probably not ready to be translated).
    """

    def __init__(self, message=None):
        self.message = message


class BundleExistsAlreadyException(Exception):
    """
    Exception thrown when an attempt to add a bundle to the manager exists but
    a bundle with that code exists already.
    """

    def __init__(self, message=None):
        self.message = message