"""
The DB module deals with database connection issues and with Alembic.
Note that we have chosen not to use flask-sqlalchemy extension to
reduce the number of dependencies.
"""

import os

from sqlalchemy import create_engine

from flask.ext.sqlalchemy import SQLAlchemy
from .application import app

db = SQLAlchemy()
db.init_app(app)
session = db.session


def init_db(drop=False):
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    if drop:
        print "Dropping Database"
        db.session.drop_all(app=app)
    db.session.create_all(app=app)
    db.session.commit()


from alembic.script import ScriptDirectory
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic import command


class DbParticularUpgrader(object):
    def __init__(self):
        self.config = Config("alembic.ini")
        self.config.set_main_option("script_location", os.path.abspath('alembic'))
        self.config.set_main_option("url", app.config['SQLALCHEMY_DATABASE_URI'])
        self.config.set_main_option("sqlalchemy.url", app.config['SQLALCHEMY_DATABASE_URI'])

    @property
    def head(self):
        script = ScriptDirectory.from_config(self.config)
        return script.get_current_head()

    def check(self):
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

        context = MigrationContext.configure(engine)
        current_rev = context.get_current_revision()

        return self.head == current_rev

    def upgrade(self):
        if not self.check():
            command.upgrade(self.config, "head")


upgrader = DbParticularUpgrader()

