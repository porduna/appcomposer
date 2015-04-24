import goslate
import json
from appcomposer import db, app
from appcomposer.models import ActiveTranslationMessage, TranslationBundle, TranslationExternalSuggestion

gs = goslate.Goslate()

DATABASE = True

LANG = 'eu'

FILE = 'langs.json'

def load():
    try:
        return json.load(open(FILE))
    except:
        print "File not found, starting from scratch"
        return {}

def save(messages):
    open(FILE, 'w').write(json.dumps(messages, indent = 4))

MESSAGES = load()

with app.app_context():
    bundles = db.session.query(TranslationBundle).filter_by(language = 'en_ALL').all()
    active_messages = set()
    for bundle in bundles:
        for message in bundle.active_messages:
            active_messages.add(message.value)
    
    for pos, message in enumerate(active_messages):
        if pos % 30 == 0:
            print "Translating app %s of %s..." % (pos, len(active_messages))

        if DATABASE:
            existing_suggestion = db.session.query(TranslationExternalSuggestion).filter_by(engine = 'google', human_key = message, language = LANG, origin_language = 'en_ALL').first()
        else:
            existing_suggestion = MESSAGES.get(message)

        if existing_suggestion is None:
            translated = gs.translate(message, LANG)
            if translated:
                if DATABASE:
                    suggestion = TranslationExternalSuggestion(engine = 'google', human_key = message, language = LANG, origin_language = 'en_ALL', value = translated)
                    db.session.add(suggestion)
                    db.session.commit()
                else:
                    MESSAGES[message] = translated
                    save(MESSAGES)
