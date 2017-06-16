import babel

#
# Use @public to mark that a method is intentionally public
# 
def public(func): return func

# This is a dictionary like { 'English' : 'en', 'French' : 'fr' ...}
LANGUAGES_PER_NAME = { v: k for k, v in babel.Locale('en').languages.items() }
LANGUAGE_NAMES_PER_CODE = { k: v for k, v in babel.Locale('en').languages.items() }

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

