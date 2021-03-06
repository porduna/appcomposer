"""ADd cascades

Revision ID: def46e09c9ef
Revises: 3efdb537f933
Create Date: 2017-12-28 11:44:14.263012

"""

# revision identifiers, used by Alembic.
revision = 'def46e09c9ef'
down_revision = '3efdb537f933'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(u'RepositoryApp2languages_ibfk_2', 'RepositoryApp2languages', type_='foreignkey')
    op.drop_constraint(u'RepositoryApp2languages_ibfk_1', 'RepositoryApp2languages', type_='foreignkey')
    op.create_foreign_key(None, 'RepositoryApp2languages', 'RepositoryApps', ['repository_app_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
    op.create_foreign_key(None, 'RepositoryApp2languages', 'Languages', ['language_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
    op.drop_constraint(u'RepositoryAppCheckUrls_ibfk_1', 'RepositoryAppCheckUrls', type_='foreignkey')
    op.create_foreign_key(None, 'RepositoryAppCheckUrls', 'RepositoryApps', ['repository_app_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
    op.drop_constraint(u'RepositoryAppFailures_ibfk_1', 'RepositoryAppFailures', type_='foreignkey')
    op.create_foreign_key(None, 'RepositoryAppFailures', 'RepositoryAppCheckUrls', ['repository_app_check_url_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'RepositoryAppFailures', type_='foreignkey')
    op.create_foreign_key(u'RepositoryAppFailures_ibfk_1', 'RepositoryAppFailures', 'RepositoryAppCheckUrls', ['repository_app_check_url_id'], ['id'])
    op.drop_constraint(None, 'RepositoryAppCheckUrls', type_='foreignkey')
    op.create_foreign_key(u'RepositoryAppCheckUrls_ibfk_1', 'RepositoryAppCheckUrls', 'RepositoryApps', ['repository_app_id'], ['id'])
    op.drop_constraint(None, 'RepositoryApp2languages', type_='foreignkey')
    op.drop_constraint(None, 'RepositoryApp2languages', type_='foreignkey')
    op.create_foreign_key(u'RepositoryApp2languages_ibfk_1', 'RepositoryApp2languages', 'Languages', ['language_id'], ['id'])
    op.create_foreign_key(u'RepositoryApp2languages_ibfk_2', 'RepositoryApp2languages', 'RepositoryApps', ['repository_app_id'], ['id'])
    # ### end Alembic commands ###
