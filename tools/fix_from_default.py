import datetime
from appcomposer import app
from appcomposer.db import db
from appcomposer.models import ActiveTranslationMessage, TranslationBundle, TranslationMessageHistory
from appcomposer.translator.ops import get_golab_default_user


with app.app_context():
    total = 0
    for bundle in db.session.query(TranslationBundle).all():
        if bundle.language == 'en_ALL':
            continue

        if not bundle.from_developer:
            continue

        original_bundle = ([ b for b in bundle.translation_url.bundles if b.language == 'en_ALL' and b.target == 'ALL' ] or [None])[0]
        if original_bundle is None:
            continue
        
        original_messages = {
            # key: value
        }
        for active_message in original_bundle.active_messages:
            original_messages[active_message.key] = active_message.value
        
        for active_message in bundle.active_messages:
            if active_message.value == '{0}':
                continue

            if not active_message.taken_from_default and active_message.from_developer and active_message.value == original_messages.get(active_message.key, '________this.will.never.be'):
                total += 1
                print "Processing {0}::{1}_{2}::{3} ({4!r})".format(bundle.translation_url.url, bundle.language, bundle.target, active_message.key, active_message.value)
                ph = active_message.history
                new_history = TranslationMessageHistory(bundle = ph.bundle, key = ph.key, value = ph.value, user = get_golab_default_user(), datetime = datetime.datetime.utcnow(), parent_translation_id = ph.id, taken_from_default = True, same_tool = ph.same_tool, tool_id = ph.tool_id, fmt = ph.fmt, position = ph.position, category = ph.category, from_developer = ph.from_developer, namespace = ph.namespace)
                db.session.add(new_history)
                db.session.flush()
                db.session.refresh(new_history)
                am = active_message
                new_active_message = ActiveTranslationMessage(bundle = bundle, key = am.key, value = am.value, history = new_history, datetime = datetime.datetime.utcnow(), taken_from_default = True, position = am.position, category = am.category, from_developer = am.from_developer, namespace = am.namespace, tool_id = am.tool_id, same_tool = am.same_tool, fmt = am.fmt)
                db.session.delete(active_message)
                db.session.add(new_active_message)

    db.session.commit()
    print("{0} records processed".format(total))
