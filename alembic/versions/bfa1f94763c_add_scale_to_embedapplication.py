"""Add scale to EmbedApplication

Revision ID: bfa1f94763c
Revises: 4db77f01caa4
Create Date: 2015-11-28 19:54:10.782133

"""

# revision identifiers, used by Alembic.
revision = 'bfa1f94763c'
down_revision = '4db77f01caa4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('EmbedApplications', sa.Column('scale', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('EmbedApplications', 'scale')
    ### end Alembic commands ###
