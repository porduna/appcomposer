"""Supports offline?

Revision ID: f6506f6b35dd
Revises: 72dd4cdad196
Create Date: 2019-06-26 10:08:22.563422

"""

# revision identifiers, used by Alembic.
revision = 'f6506f6b35dd'
down_revision = '72dd4cdad196'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('RepositoryApps', sa.Column('offline', sa.Boolean(), nullable=True))
    op.create_index(op.f('ix_RepositoryApps_offline'), 'RepositoryApps', ['offline'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_RepositoryApps_offline'), table_name='RepositoryApps')
    op.drop_column('RepositoryApps', 'offline')
    # ### end Alembic commands ###
