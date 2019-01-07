"""delete English history records over 50

Revision ID: d5126053d47e
Revises: bbe219b77366
Create Date: 2019-01-06 18:12:12.357726

"""

# revision identifiers, used by Alembic.
revision = 'd5126053d47e'
down_revision = 'bbe219b77366'

import sys
import time
from alembic import op
import sqlalchemy as sa
import sqlalchemy.sql as sql

metadata = sa.MetaData()
translation_urls = sa.Table('TranslationUrls', metadata,
    sa.Column('id', sa.Integer()),
    sa.Column('url', sa.Unicode(255)),
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
    sa.Column('key', sa.Unicode(255)),
    sa.Column('datetime', sa.DateTime()),
)

def dbg(message):
    print "[{}] {}".format(time.asctime(), message)
    sys.stdout.flush()

def upgrade():
    # Take only English bundles
    all_bundles_stmt = sql.select([
            translation_bundles.c.id, 
            translation_bundles.c.language, 
            translation_bundles.c.target, 
            translation_bundles.c.translation_url_id
        ], translation_bundles.c.language == 'en_ALL')

    N = 50

    for bundle_row in list(op.get_bind().execute(all_bundles_stmt)):
        bundle_id = bundle_row[translation_bundles.c.id]
        count_total = list(op.get_bind().execute(sql.select([sa.func.count(message_history.c.id)], message_history.c.bundle_id == bundle_id)))[0][0]
        if count_total > 1000: # Only focus on the ones with more than 1000 revisions
            dbg("Big bundle. Analyzing")
            dbg(" - Data: {} {}".format(bundle_row, count_total))
            keys = [ key for key, in op.get_bind().execute(sql.select([sa.func.distinct(message_history.c.key)], message_history.c.bundle_id == bundle_id)) ]
            dbg(" - Keys: {}".format(len(keys)))
            for key in keys:
                records_found = list(op.get_bind().execute(sql.select([sa.func.count(message_history.c.id)], sa.and_(message_history.c.key == unicode(key), message_history.c.bundle_id == bundle_id))))[0][0]
                if records_found > N:
                    dbg("   - Key {} has {} records".format(key, records_found))

                    while records_found > N:
                        cut_in = records_found - N
                        if cut_in > 200:
                            cut_in = 200

                        records_found = records_found - cut_in
                        ids_to_remove_stmt = sql.select([message_history.c.id, message_history.c.datetime], sa.and_(message_history.c.key == unicode(key), message_history.c.bundle_id == bundle_id)).order_by(sa.asc(message_history.c.datetime)).limit(cut_in)
                        ids_to_remove = [ id_to_remove for id_to_remove, record_datetime in op.get_bind().execute(ids_to_remove_stmt) ]
                        dbg("     - Deleting {} of them... after: {}".format(cut_in, records_found))
                        op.get_bind().execute(message_history.delete(message_history.c.id.in_(ids_to_remove)))


def downgrade():
    pass
