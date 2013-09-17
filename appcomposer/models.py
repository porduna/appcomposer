import uuid
import datetime

from flask.ext.login import UserMixin

from sqlalchemy import Column, Integer, Unicode, sql, UniqueConstraint, DateTime, ForeignKey, Text
from sqlalchemy.orm import relation, backref

from appcomposer.db import Base, db_session as DBS

class User(Base, UserMixin):
    __tablename__ = 'Users'

    id = Column(Integer, primary_key=True)

    login    = Column(Unicode(50), unique = True )
    name     = Column(Unicode(50), nullable = False)
    password = Column(Unicode(50), nullable = False) # hash

    def __init__(self, login = None, name = None, password = None):
        self.login    = login
        self.name     = name
        self.password = password

    def __repr__(self):
        return "User(%r, %r, %r, %r)" % (self.login, self.name, self.password)

    def __unicode__(self):
        return self.name

    @classmethod
    def exists(self, login, word):
        return DBS.query(self).filter(sql.and_(self.login == login, self.password == word)).first()

class App(Base):

    __tablename__ = 'Apps'
    __table_args__ = (UniqueConstraint('name', 'owner_id'), )

    id = Column(Integer, primary_key = True)

    unique_id         = Column(Unicode(50), index = True, unique = True)
    name              = Column(Unicode(50), index = True)
    owner_id          = Column(Integer, ForeignKey("Users.id"), nullable = False, index = True)
    composer          = Column(Unicode(50), index = True, nullable = False, server_default = u'expert')
    data              = Column(Text, nullable = False, server_default = u'{}')
    creation_date     = Column(DateTime, nullable = False, index = True)
    modification_date = Column(DateTime, nullable = False, index = True)
    last_access_date  = Column(DateTime, nullable = False, index = True)

    owner = relation("User", backref=backref("own_apps", order_by=id, cascade='all,delete'))

    def __init__(self, name, owner):
        self.name  = name
        self.owner = owner
        self.creation_date = self.modification_date = self.last_access_date = datetime.datetime.now()

        self.unique_id = str(uuid.uuid4())
        while App.find_by_unique_id(self.unique_id) is not None:
            self.unique_id = str(uuid.uuid4())
        
    @classmethod
    def find_by_unique_id(self, unique_id):
        return DBS.query(self).filter(unique_id = unique_id).first()

