"""add unique in bundles

Revision ID: d20615919d80
Revises: b262149925a7
Create Date: 2017-10-14 17:04:29.450667

"""

# revision identifiers, used by Alembic.
revision = 'd20615919d80'
down_revision = 'b262149925a7'

from collections import defaultdict

from alembic import op
import sqlalchemy as sa
from sqlalchemy import func

from appcomposer.db import db
from appcomposer.application import app

metadata = db.MetaData()
ActiveTranslationMessage = db.Table('ActiveTranslationMessages', metadata,
    sa.Column('id', sa.Integer, nullable=True),
    sa.Column('bundle_id', sa.Integer, nullable=False),
)

TranslationMessageHistory = db.Table('TranslationMessageHistory', metadata,
    sa.Column('id', sa.Integer, nullable=True),
    sa.Column('bundle_id', sa.Integer, nullable=False),
)

TranslationBundle = db.Table('TranslationBundles', metadata,
    sa.Column('id', sa.Integer, nullable=True),
    sa.Column('translation_url_id', sa.Integer, nullable=False),
    sa.Column('language', sa.Unicode(20), nullable=False),
    sa.Column('target', sa.Unicode(20), nullable=False),
)

def upgrade():
    with app.app_context():
        duplicated_bundles = list(db.session.query(TranslationBundle.c.translation_url_id, TranslationBundle.c.language, TranslationBundle.c.target).group_by(TranslationBundle.c.translation_url_id, TranslationBundle.c.language, TranslationBundle.c.target).having(func.count(TranslationBundle.c.id) > 1).all())
        translation_url_ids = [ tr_id for tr_id, language, target in duplicated_bundles ]
        languages = [ language for tr_id, language, target in duplicated_bundles ]
        targets = [ target for tr_id, language, target in duplicated_bundles ]

        all_results = defaultdict(list)

        for bundle in db.session.query(TranslationBundle).filter(TranslationBundle.c.translation_url_id.in_(translation_url_ids), TranslationBundle.c.language.in_(languages), TranslationBundle.c.target.in_(targets)).all():
            all_results[bundle.translation_url_id, bundle.language, bundle.target].append(bundle)

        all_bundle_ids = []
        for key in duplicated_bundles:
            for bundle in all_results[key][1:]:
                all_bundle_ids.append(bundle.id)

    delete_msg_stmt = ActiveTranslationMessage.delete(ActiveTranslationMessage.c.bundle_id.in_(all_bundle_ids))
    delete_hist_stmt = TranslationMessageHistory.delete(TranslationMessageHistory.c.bundle_id.in_(all_bundle_ids))
    delete_bundle_stmt = TranslationBundle.delete(TranslationBundle.c.id.in_(all_bundle_ids))
    connection = op.get_bind()
    connection.execute(delete_msg_stmt)
    connection.execute(delete_hist_stmt)
    connection.execute(delete_bundle_stmt)

    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'TranslationBundles', ['translation_url_id', 'language', 'target'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'TranslationBundles', type_='unique')
    # ### end Alembic commands ###
