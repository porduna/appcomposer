import os
import hashlib

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from config import SQLALCHEMY_ENGINE_STR, USE_PYMYSQL

if USE_PYMYSQL:
    import pymysql_sa
    pymysql_sa.make_default_mysql_dialect()

engine = create_engine(SQLALCHEMY_ENGINE_STR, convert_unicode=True, pool_recycle=3600)

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def init_db(drop = False):
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    from .models import User
    from .models import App

    if drop:
        print "Droping Database"
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    password = unicode(hashlib.new('sha', 'password').hexdigest())
    admin_user = User(u'admin', u'Administrator', password)
    db_session.add(admin_user)
    db_session.commit()


from alembic.script import ScriptDirectory
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic import command

class DbParticularUpgrader(object):

    def __init__(self):
        self.config = Config("alembic.ini")
        self.config.set_main_option("script_location", os.path.abspath('alembic'))
        self.config.set_main_option("url", SQLALCHEMY_ENGINE_STR)
        self.config.set_main_option("sqlalchemy.url", SQLALCHEMY_ENGINE_STR)

    @property
    def head(self):
        script = ScriptDirectory.from_config(self.config)
        return script.get_current_head()

    def check(self):
        engine = create_engine(SQLALCHEMY_ENGINE_STR)

        context = MigrationContext.configure(engine)
        current_rev = context.get_current_revision()

        return self.head == current_rev

    def upgrade(self):
        if not self.check():
            command.upgrade(self.config, "head")

upgrader = DbParticularUpgrader()

