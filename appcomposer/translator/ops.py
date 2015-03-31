import pprint

def add_full_translation_to_app(user, app_url, translation_url, language, target, translated_messages, original_messages):
    print "Task:"
    print "App url:", app_url
    print "Translation URL:", translation_url
    print "Language:", language
    print "Target:", target
    print "Translated messages"
    pprint.pprint(translated_messages)
    print "Original messages"
    pprint.pprint(original_messages)
