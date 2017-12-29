"""
To contain language-related ops.
"""
from collections import OrderedDict
import babel
from babel import Locale, UnknownLocaleError
from appcomposer.i18n import gettext
from flask import request


def obtain_groups():
    """
    Obtains the groups that are available for translation, as an Ordered Dictionary.

    :return: Ordered dictionary with the name of the groups identified by each key.
    :rtype: OrderedDict
    """
    groups = OrderedDict()
    groups["ALL"] = "ALL"
    groups["10-13"] = gettext("Preadolescence (age 10-13)")
    groups["14-18"] = gettext("Adolescence (age 14-18)")
    return groups

# Taken from http://en.wikipedia.org/wiki/Languages_of_the_European_Union, April 2015
OFFICIAL_EUROPEAN_UNION_LANGUAGES = ['bg', 'hr', 'cs', 'da', 'nl', 'en', 'et', 'fi', 'fr', 'de', 'el', 'hu', 'ga', 'it', 'lv', 'lt', 'mt', 'pl', 'pt', 'ro', 'sk', 'sl', 'es', 'sv']
SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES = ['eu', 'ca', 'gl', 'gd', 'cy']
OTHER_LANGUAGES = [
    # The following languages are in Graasp
    'uk', # Ukranian
    'tr', # Turkish
    'sr', # Serbian language
    'ru', # Russian language
    'be', # Belarussian
    # The following languages are too widely used
    'ar', # Arabic
    'zh', # Chinese
    'hi', # Hindi
    # The following were available in the Go-Lab portal
    'bs', # Bosnian
    'sh', # Serbo-Croatian,
    'lb', # Luxembourgish,
    'se', # Northern Sami
    # The following have been selected to be interesting for Go-Lab
    'no', # Norwegian
    'id', # Indonesian
    'ja', # Japanese
    'my', # Burmese
    'mk', # Macedonian
    'he', # Hebrew
]

ALL_LANGUAGES = OFFICIAL_EUROPEAN_UNION_LANGUAGES + SEMIOFFICIAL_EUROPEAN_UNION_LANGUAGES + OTHER_LANGUAGES

def obtain_languages():
    """
    Obtains the languages (without the groups) that are available for translation,
    as a Dictionary. The format is code:language_name

    TO-DO: This method can probably be optimized.

    :return:
    """
    babel_supported_languages = babel.core.Locale("en", "US").languages.items()
    languages = []
    for code, lang in babel_supported_languages:
        golab_supported = False
        for supported_code in ALL_LANGUAGES:
            if code == supported_code:
                golab_supported = True
                break
        if golab_supported:
            languages.append( (code, lang) )
    if False:
        print "Babel Supported languages after filter: %s" % len(languages)
        print "Go-Lab Supported languages: %s" % len(ALL_LANGUAGES)
    languages.sort(key=lambda it: it[1])

    # TODO: Currently, we filter languages which contain "_" in their code so as to simplify.
    # Because we use _ throughout the composer as a separator character, trouble is caused otherwise.
    # Eventually we should consider whether we need to support special languages with _
    # on its code.
    targetlangs_codes = [lang[0] + "_ALL" for lang in languages if "_" not in lang[0]]

    targetlangs_list = [{"pcode": code, "repr": get_locale_english_name(
        *get_locale_info_from_code(code))} for code in targetlangs_codes]

    d = {lang["pcode"]: lang["repr"] for lang in targetlangs_list}
    d["all_ALL"] = "DEFAULT"
    return d

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

def get_locale_english_name(lang, country):
    """
    Retrieves a string representation of a Locale.
    @param lang: Lang code.
    @param country: Country code.
    @return: String representation for the locale.
    """
    if lang == 'mk':
        return u'Macedonian Slavic'
    try:
        if country.upper() == 'ALL':
            country = ""
        return Locale(lang, country).english_name
    except UnknownLocaleError:
        return Locale("en", "US").languages.get(lang)

class UnrecognizedLocaleCodeException(Exception):
    """
    Exception thrown when the format of a locale code does not seem to be
    as expected.
    """

LANGUAGES = obtain_languages()
# This is a dictionary like { 'English' : 'en', 'French' : 'fr' ...}
LANGUAGES_PER_NAME = { v: k for k, v in babel.Locale('en').languages.items() }
LANGUAGE_NAMES_PER_CODE = { k: v for k, v in babel.Locale('en').languages.items() }
LANGUAGES_ORDER = (
                # Official languages
                ['English', 'German', 'French', 'Italian', 'Spanish', 'Polish', 'Romanian', 'Dutch', 'Hungarian', 'Portuguese', 'Greek', 'Swedish', 'Czech', 'Bulgarian', 'Slovak', 'Danish', 'Finnish', 'Lithuanian', 'Slovene', 'Slovenian', 'Estonian', 'Croatian', 'Irish', 'Latvian', 'Maltese'] 
                # Semi-official languages
                + ['Catalan', 'Galician', 'Basque', 'Scottish Gaelic', 'Luxembourgish', 'Luxembourgeois', 'Welsh'] 
                # + Most used foreign languages
                + ['Russian', 'Arabic', 'Turkish', 'Tamil', 'Chinese', 'Japanese', 'Korean', 'Hindi', 'Urdu']
        )

# Sometimes in golabz some languages are displayed in a format not supported by babel
# Here is a translation for those known issues
WRONG_LANGUAGES = {
    'Serbo Croatian' : 'Serbo-Croatian',
    'Luxembourgeois' : 'Luxembourgish',
    'Slovene': 'Slovenian',
}

WRONG_LANGUAGES_PER_CORRECT_NAME = {}
for wrong_name, correct_name in WRONG_LANGUAGES.items():
    if correct_name in WRONG_LANGUAGES_PER_CORRECT_NAME:
        WRONG_LANGUAGES_PER_CORRECT_NAME[correct_name].append(wrong_name)
    else:
        WRONG_LANGUAGES_PER_CORRECT_NAME[correct_name] = [ wrong_name ]

# Given this percentage, the AppComposer will decide whether to report if an app has been updated or not.
LANGUAGE_THRESHOLD = 0.8

def sort_languages(languages):
    """
    Given a list of languages in English; e.g.: [ 'Spanish', 'Welsh', 'English']
    sort the list of languages by population speaking it according to:

    https://en.wikipedia.org/wiki/Languages_of_the_European_Union#Knowledge

    and return such list.
    """
    old_languages = list(languages)
    new_languages = []
    # sorted as suggested in Wikipedia
    for lang in LANGUAGES_ORDER:
        if lang in old_languages:
            old_languages.remove(lang)
            new_languages.append(lang)

    new_languages.extend(sorted(old_languages))

    return new_languages

def guess_default_language():
    best_match = request.accept_languages.best_match([ lang_code.split('_')[0] for lang_code in LANGUAGES ])
    default_language = None
    if best_match is not None:
        if best_match in LANGUAGES:
            default_language = best_match
        else:
            lang_codes = [ lang_code for lang_code in LANGUAGES if lang_code.startswith('%s_' % best_match) ]
            if lang_codes:
                default_language = lang_codes[0]
    return default_language


