"""
To contain language-related ops.
"""
from collections import OrderedDict
import babel
from appcomposer.babel import gettext
from appcomposer.composers.translate.bundles import BundleManager


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

def obtain_languages():
    """
    Obtains the languages (without the groups) that are available for translation,
    as a Dictionary. The format is code:language_name

    :return:
    """
    targetlangs = obtain_targetlangs_list()
    return {lang["pcode"]: lang["repr"] for lang in targetlangs}


def obtain_targetlangs_list():
    """
    Obtains the targetlangs_list. This function SHOULD EVENTUALLY BE REMOVED.
    :return:
    """
    languages = babel.core.Locale("en", "US").languages.items()
    languages.sort(key=lambda it: it[1])

    # TODO: Currently, we filter languages which contain "_" in their code so as to simplify.
    # Because we use _ throughout the composer as a separator character, trouble is caused otherwise.
    # Eventually we should consider whether we need to support special languages with _
    # on its code.
    targetlangs_codes = [lang[0] + "_ALL" for lang in languages if "_" not in lang[0]]

    targetlangs_list = [{"pcode": code, "repr": BundleManager.get_locale_english_name(
        *BundleManager.get_locale_info_from_code(code))} for code in targetlangs_codes]

    return targetlangs_list