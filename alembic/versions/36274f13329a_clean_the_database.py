"""Clean the database

Revision ID: 36274f13329a
Revises: 9aea6784a701
Create Date: 2019-01-03 23:46:35.648015

"""

# revision identifiers, used by Alembic.
revision = '36274f13329a'
down_revision = '9aea6784a701'

import time
from alembic import op
import sqlalchemy as sa
import sqlalchemy.sql as sql

metadata = sa.MetaData()
translated_apps = sa.Table('TranslatedApps', metadata,
    sa.Column('id', sa.Integer()),
    sa.Column('translation_url_id', sa.Integer()),
    sa.Column('url', sa.Unicode(255)),
)

translation_urls = sa.Table('TranslationUrls', metadata,
    sa.Column('id', sa.Integer()),
    sa.Column('url', sa.Unicode(255)),
)

translation_subscriptions = sa.Table('TranslationSubscriptions', metadata,
    sa.Column('id', sa.Integer()),
    sa.Column('translation_url_id', sa.Integer()),
)

translation_bundles = sa.Table('TranslationBundles', metadata,
    sa.Column('id', sa.Integer()),
    sa.Column('language', sa.Unicode(20)),
    sa.Column('target', sa.Unicode(20)),
    sa.Column('translation_url_id', sa.Integer()),
)

message_history = sa.Table('TranslationMessageHistory', metadata,
    sa.Column('id', sa.Integer()),
    sa.Column('bundle_id', sa.Integer()),
)

active_messages = sa.Table('ActiveTranslationMessages', metadata,
    sa.Column('id', sa.Integer()),
    sa.Column('bundle_id', sa.Integer()),
)

def dbg(message):
    print "[{}] {}".format(time.asctime(), message)

def upgrade():
    old_app_urls = [
        'http://go-lab.gw.utwente.nl/sources/tools/conceptmap/src/main/webapp/conceptmapper.xml',
        'http://go-lab.gw.utwente.nl/production/questioning_v1/tools/questioning/src/main/webapp/questioning.xml',
        'http://go-lab.gw.utwente.nl/production/hypothesis_v1/tools/hypothesis/src/main/webapp/hypothesis.xml',
        'http://go-lab.gw.utwente.nl/production/hypothesis_v1/tools/hypothesis/src/main/webapp/hypothesis_electricity.xml',
        'http://go-lab.gw.utwente.nl/production/conceptmapper_v1/tools/conceptmap/src/main/webapp/conceptmapper.xml',
        'http://go-lab.gw.utwente.nl/production/splash/labs/splash/virtual.xml',
        'http://go-lab.gw.utwente.nl/production/edt/tools/edt/edt.xml',
        'http://go-lab.gw.utwente.nl/production/reflect/tools/reflect/reflect.xml'
    ]

    translation_url_ids = []

    for app_url in old_app_urls:
        dbg("Processing {}".format(app_url))
        find_translated_app_stmt = sql.select([translated_apps.c.id, translated_apps.c.translation_url_id], translated_apps.c.url == app_url)
        rows = list(op.get_bind().execute(find_translated_app_stmt))
        if len(rows) == 0:
            dbg("Not found")
            continue
        translated_app_id = rows[0][translated_apps.c.id]
        translation_url_id = rows[0][translated_apps.c.translation_url_id]

        find_translation_url_stmt = sql.select([translation_urls.c.url], translation_urls.c.id == translation_url_id)
        rows = list(op.get_bind().execute(find_translation_url_stmt))
        translation_url_url = rows[0][translation_urls.c.url]
        dbg(" - Translation URL: {} ( {} )".format(translation_url_id, translation_url_url))
        dbg(" - Translated App id: {}".format(translated_app_id))
        
        find_other_translated_apps_stmt = sql.select([translated_apps.c.id, translated_apps.c.url], translated_apps.c.translation_url_id == translation_url_id)
        rows = list(op.get_bind().execute(find_other_translated_apps_stmt))
        if len(rows) > 1:
            found = []
            for row in rows:
                other_translated_app_url = row[translated_apps.c.url]
                if other_translated_app_url in old_app_urls:
                    # If all the URLs are in the list, no problem
                    continue

            if found:
                dbg("There is another app using this translation URL: {}: {}".format(translation_url_id, found))
                continue

        translation_url_ids.append(translation_url_id)

        # Now we now that for this specific TranslationUrl, there is nobody else using it. First find the bundles
        find_translation_bundles_stmt = sql.select([translation_bundles.c.id, translation_bundles.c.language, translation_bundles.c.target], translation_bundles.c.translation_url_id == translation_url_id)
        for bundle_id, language, target in list(op.get_bind().execute(find_translation_bundles_stmt)):
            dbg(" - Processing bundle {} ({}/{})".format(bundle_id, language, target))
            dbg("   - Deleting active messages of bundle {}".format(bundle_id))
            # Delete all active messages
            active_messages_stmt = active_messages.delete(active_messages.c.bundle_id == bundle_id)
            op.get_bind().execute(active_messages_stmt)

            dbg("   - Deleting history messages of bundle {}".format(bundle_id))
            # Delete all history messages
            message_history_stmt= message_history.delete(message_history.c.bundle_id == bundle_id)
            op.get_bind().execute(message_history_stmt)

            dbg("   - Deleting bundle itself")
            op.get_bind().execute(translation_bundles.delete(translation_bundles.c.id == bundle_id))

        dbg(" - All bundles deleted. Proceeding with the TranslatedApp")
        op.get_bind().execute(translated_apps.delete(translated_apps.c.id == translated_app_id))
        dbg(" - And with subscriptions")
        op.get_bind().execute(translation_subscriptions.delete(translation_subscriptions.c.translation_url_id == translation_url_id))
        dbg(" - Finished with the app")

    for translation_url_id in translation_url_ids:
        dbg("Deleting TranslationUrl")
        op.get_bind().execute(translation_urls.delete(translation_urls.c.id == translation_url_id))



def downgrade():
    pass
