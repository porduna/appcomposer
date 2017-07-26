"""Add primary key to RepositoryApp2languages

Revision ID: 331f2c45f5a
Revises: b100c13976f
Create Date: 2017-07-25 16:48:31.860599

"""

# revision identifiers, used by Alembic.
revision = '331f2c45f5a'
down_revision = 'b100c13976f'

from alembic import op
from sqlalchemy import Integer, and_
from sqlalchemy.sql import column, table, select
import sqlalchemy as sa

RepositoryApp2languages = table('RepositoryApp2languages',
    column('id', Integer),
    column('repository_app_id', Integer),
    column('language_id', Integer),
)

def upgrade():
    elements = [
#         {
#             'repository_app_id': number,
#             'language_id': number,
#         }
    ]
    connection = op.get_bind()
    for repository_app_id, language_id in connection.execute(select([RepositoryApp2languages.c.repository_app_id, RepositoryApp2languages.c.language_id])):
        elements.append({
            'repository_app_id': repository_app_id,
            'language_id' : language_id,
        })

    for pos, element in enumerate(elements):
        stmt = RepositoryApp2languages.update().where(
                        and_(
                            RepositoryApp2languages.c.repository_app_id==element['repository_app_id'], 
                            RepositoryApp2languages.c.language_id == element['language_id']
                        )).values({ 'id': pos + 1 })
        op.execute(stmt)
        
    op.create_primary_key( "pk_my_table", "RepositoryApp2languages", ["id"])


def downgrade():
    pass
