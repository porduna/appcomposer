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

    if drop:
        print "Droping Database"
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    password = unicode(hashlib.new('sha', 'password').hexdigest())
    admin_user = User(u'admin', u'Administrator', password)
    db_session.add(admin_user)
    db_session.commit()

