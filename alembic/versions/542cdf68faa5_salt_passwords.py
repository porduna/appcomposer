"""Salt passwords

Revision ID: 542cdf68faa5
Revises: 26745016c3ce
Create Date: 2014-04-16 15:15:05.393213

"""

import string
import random
from hashlib import new as new_hash

# revision identifiers, used by Alembic.
revision = '542cdf68faa5'
down_revision = '26745016c3ce'

from alembic import op
import sqlalchemy as sa
import sqlalchemy.sql as sql

def create_salted_password(password):
    alphabet = string.ascii_letters + string.digits
    CHARS = 6
    random_str = ""
    for _ in range(CHARS):
        random_str += random.choice(alphabet)

    salted_password = unicode(new_hash("sha", random_str + password).hexdigest())
    return random_str + "::" + salted_password

metadata = sa.MetaData()
user = sa.Table('Users', metadata,
    sa.Column('id', sa.Integer()),
    sa.Column('auth_system', sa.Unicode(20)),
    sa.Column('auth_data', sa.String(255)),
)

def upgrade():
    users_data = sql.select([user.c.id, user.c.auth_data], user.c.auth_system == "userpass")

    user_passwords = {}
    for row in op.get_bind().execute(users_data):
        user_passwords[row[user.c.id]] = row[user.c.auth_data]

    for user_id in user_passwords:
        new_password = create_salted_password( user_passwords[user_id] )
        update_stmt = user.update().where(user.c.id == user_id).values(auth_data = new_password)
        op.execute(update_stmt)

def downgrade():
    pass
