"""Add autoincrement

Revision ID: 73b63ad41d3
Revises: 331f2c45f5a
Create Date: 2017-07-25 17:09:55.204538

"""

# revision identifiers, used by Alembic.
revision = '73b63ad41d3'
down_revision = '331f2c45f5a'

from alembic import op
from sqlalchemy import Integer
import sqlalchemy as sa


def upgrade():
    op.alter_column("RepositoryApp2languages", "id", existing_type=Integer, autoincrement=True, nullable=False)


def downgrade():
    pass
