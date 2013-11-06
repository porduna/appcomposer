"""Add admin user

Revision ID: 9cb5a6027a6
Revises: 247238952b94
Create Date: 2013-11-06 13:15:39.032871

"""

# revision identifiers, used by Alembic.
revision = '9cb5a6027a6'
down_revision = '247238952b94'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("INSERT INTO Users (login, name, auth_system, auth_data, password) VALUES ('admin', 'Administrator', 'userpass', 'password', 'password')")


def downgrade():
    pass
