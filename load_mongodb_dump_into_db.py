import glob
import json
import datetime

from bson.json_util import loads

from appcomposer import app
from appcomposer.translator.ops import get_golab_default_user, add_full_translation_to_app
from appcomposer.translator.utils import extract_local_translations_url

files = glob.glob("dump/*")

with app.app_context():
    user = get_golab_default_user()

    for f in files:
        print "Processing...",f,
        translation = loads(open(f).read())
        app_url = translation['spec']
        language, target = translation['bundle'].rsplit('_', 1)
        if language == 'all_ALL':
            print "Skipping all_ALL"
            continue
        elif language.startswith('af'):
            print "Skipping afghan and afrikaans"
            continue

        try:
            translated_messages = json.loads(json.loads(translation['data']))
        except (ValueError, TypeError):
            translated_messages = json.loads(translation['data'])

        if translated_messages is None or len(translated_messages) == 0:
            print "Skipping empty"
            continue

        from_developer = False

        translation_url, original_messages = extract_local_translations_url(app_url, force_local_cache = True)

        add_full_translation_to_app(user, app_url, translation_url, language, target, translated_messages, original_messages, from_developer)
        print "[done]"

