from sqlalchemy import Column, Integer, Unicode, ForeignKey, UniqueConstraint, sql, Table, Boolean
from sqlalchemy.orm import relation, backref, relationship

from flask.ext.login import UserMixin

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


