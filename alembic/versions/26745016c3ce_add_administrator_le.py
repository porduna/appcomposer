"""Add administrator level to admin

Revision ID: 26745016c3ce
Revises: 3a731ce5846e
Create Date: 2014-04-15 17:55:26.716534

"""

# revision identifiers, used by Alembic.
revision = '26745016c3ce'
down_revision = '3a731ce5846e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("UPDATE Users SET role = 'administrator' WHERE login IN ('admin', 'testuser')")



def downgrade():
    pass
