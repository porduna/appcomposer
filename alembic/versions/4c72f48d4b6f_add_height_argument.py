"""Add height argument

Revision ID: 4c72f48d4b6f
Revises: df42ba6d96
Create Date: 2015-08-01 01:01:34.108073

"""

# revision identifiers, used by Alembic.
revision = '4c72f48d4b6f'
down_revision = 'df42ba6d96'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('EmbedApplications', sa.Column('height', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('EmbedApplications', 'height')
    ### end Alembic commands ###
