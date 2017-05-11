"""Remove unused tables

Revision ID: bc497a3d230
Revises: 9440ed72930
Create Date: 2017-05-10 18:27:13.954893

"""

# revision identifiers, used by Alembic.
revision = 'bc497a3d230'
down_revision = '9440ed72930'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    try:
        op.drop_constraint(u'Apps_ibfk_2', 'Apps', type_='foreignkey')
    except:
        print("No alter in SQLite")
    try:
        op.drop_column('Apps', u'spec_id')
        op.drop_column('Apps', u'description')
    except:
        print("No alter in SQLite")

    op.drop_table(u'AppVersions')
    op.drop_table(u'Messages')
    op.drop_table(u'AppVars')
    op.drop_table(u'Bundles')
    try:
        op.drop_table(u'Specs')
    except:
        print("No alter in SQLite")

    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Apps', sa.Column(u'description', mysql.VARCHAR(length=1000), nullable=True))
    op.add_column('Apps', sa.Column(u'spec_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.create_foreign_key(u'Apps_ibfk_2', 'Apps', u'Specs', [u'spec_id'], [u'id'])
    op.create_table(u'Specs',
    sa.Column(u'id', mysql.INTEGER(display_width=11), nullable=False),
    sa.Column(u'url', mysql.VARCHAR(length=500), nullable=False),
    sa.Column(u'pid', mysql.VARCHAR(length=60), nullable=False),
    sa.PrimaryKeyConstraint(u'id'),
    mysql_default_charset=u'utf8',
    mysql_engine=u'InnoDB'
    )
    op.create_table(u'Bundles',
    sa.Column(u'id', mysql.INTEGER(display_width=11), nullable=False),
    sa.Column(u'lang', mysql.VARCHAR(length=15), nullable=True),
    sa.Column(u'target', mysql.VARCHAR(length=30), nullable=True),
    sa.Column(u'app_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint([u'app_id'], [u'Apps.id'], name=u'Bundles_ibfk_1'),
    sa.PrimaryKeyConstraint(u'id'),
    mysql_default_charset=u'utf8',
    mysql_engine=u'InnoDB'
    )
    op.create_table(u'AppVars',
    sa.Column(u'var_id', mysql.INTEGER(display_width=11), nullable=False),
    sa.Column(u'name', mysql.VARCHAR(length=50), nullable=True),
    sa.Column(u'value', mysql.VARCHAR(length=500), nullable=True),
    sa.Column(u'app_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint([u'app_id'], [u'Apps.id'], name=u'AppVars_ibfk_1'),
    sa.PrimaryKeyConstraint(u'var_id'),
    mysql_default_charset=u'utf8',
    mysql_engine=u'InnoDB'
    )
    op.create_table(u'Messages',
    sa.Column(u'id', mysql.INTEGER(display_width=11), nullable=False),
    sa.Column(u'key', mysql.VARCHAR(length=250), nullable=True),
    sa.Column(u'value', mysql.TEXT(), nullable=True),
    sa.Column(u'bundle_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint([u'bundle_id'], [u'Bundles.id'], name=u'Messages_ibfk_1'),
    sa.PrimaryKeyConstraint(u'id'),
    mysql_default_charset=u'utf8',
    mysql_engine=u'InnoDB'
    )
    op.create_table(u'AppVersions',
    sa.Column(u'version_id', mysql.INTEGER(display_width=11), nullable=False),
    sa.Column(u'app_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.Column(u'creation_date', sa.DATETIME(), nullable=False),
    sa.ForeignKeyConstraint([u'app_id'], [u'Apps.id'], name=u'AppVersions_ibfk_1'),
    sa.PrimaryKeyConstraint(u'version_id', u'app_id'),
    mysql_default_charset=u'utf8',
    mysql_engine=u'InnoDB'
    )
    ### end Alembic commands ###
