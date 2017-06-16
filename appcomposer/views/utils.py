import babel
from flask import request
from appcomposer.translator.languages import obtain_languages

#
# Use @public to mark that a method is intentionally public
# 
def public(func): return func


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

def _guess_default_language():
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


