import uuid
import datetime

from flask.ext.login import UserMixin

from sqlalchemy import Column, Integer, Unicode, sql, UniqueConstraint, DateTime, ForeignKey, Text
from sqlalchemy.orm import relation, backref

from appcomposer.db import Base, db_session as DBS

import json


class User(Base, UserMixin):
    __tablename__ = 'Users'

    id = Column(Integer, primary_key=True)

    login = Column(Unicode(50), unique=True)
    name = Column(Unicode(50), nullable=False)
    password = Column(Unicode(50), nullable=False) # hash
    email = Column(Unicode(254), nullable=False)
    organization = Column(Unicode(50))
    role = Column(Unicode(50))
    creation_date = Column(DateTime, nullable=False, index=True)
    last_access_date = Column(DateTime, nullable=False, index=True)
    auth_system = Column(Unicode(20), nullable=True)
    auth_data = Column(Unicode(255), nullable=True)

    def __init__(self, login=None, name=None, password=None, email=None, organization=None, role=None,
                 creation_date=None, last_access_date=None, auth_system=None, auth_data=None):
        self.login = login
        self.name = name
        self.password = password
        self.email = email
        self.organization = organization
        self.role = role
        self.creation_date = creation_date
        self.last_access_date = last_access_date
        self.auth_system = auth_system
        self.auth_data = auth_data

    def __repr__(self):
        return "User(%r, %r, %r, %r, %r, %r, %r, %r, %r, %r)" % (
            self.login, self.name, self.password, self.email, self.organization, self.role, self.creation_date,
            self.last_access_date, self.auth_system, self.auth_data)

    def __unicode__(self):
        return self.name

    @classmethod
    def exists(cls, login, word):
        return DBS.query(cls).filter(sql.and_(cls.login == login, cls.password == word)).first()


class AppVersion(Base):
    __tablename__ = 'AppVersions'

    version_id = Column(Integer, primary_key=True)
    app_id = Column(Integer, ForeignKey("Apps.id"), primary_key=True)
    creation_date = Column(DateTime, nullable=False, index=True)

    app = relation("App", backref="app_versions")

    def __init__(self, version_id, app):
        self.version_id = version_id
        self.app = app
        self.creation_date = datetime.datetime.now()


# TODO: Changes to consider:
# - Remove id column
# - Make unique_id primary key
# - Remove owner_id ( I think the "owner" relation covers this already? )
class App(Base):
    __tablename__ = 'Apps'
    __table_args__ = (UniqueConstraint('name', 'owner_id'), )

    id = Column(Integer, primary_key=True)

    unique_id = Column(Unicode(50), index=True, unique=True)
    name = Column(Unicode(50), index=True)
    owner_id = Column(Integer, ForeignKey("Users.id"), nullable=False, index=True)
    composer = Column(Unicode(50), index=True, nullable=False, server_default=u'expert')
    data = Column(Text, nullable=False, server_default=u'{}')
    creation_date = Column(DateTime, nullable=False, index=True)
    modification_date = Column(DateTime, nullable=False, index=True)
    last_access_date = Column(DateTime, nullable=False, index=True)

    owner = relation("User", backref=backref("own_apps", order_by=id, cascade='all,delete'))

    def __init__(self, name=None, owner=None, composer=None):
        self.name = name
        self.owner = owner
        self.composer = composer
        self.creation_date = self.modification_date = self.last_access_date = datetime.datetime.now()

        self.unique_id = str(uuid.uuid4())
        while App.find_by_unique_id(self.unique_id) is not None:
            self.unique_id = str(uuid.uuid4())

    def to_dict(self):
        """
        Turns the app into a dictionary with just data (which is easy to serialize).
        """
        d = {
            "unique_id": self.unique_id,
            "name": self.name,
            "owner_id": self.owner_id,
            "composer": self.composer,
            "data": self.data,
            "creation_date": self.creation_date.__str__(),
            "modification_date": self.modification_date.__str__(),
            "last_access_date": self.last_access_date.__str__()
        }
        return d

    def to_json(self):
        """
        Turns the App into a JSON string.
        """
        return json.dumps(self.to_dict())

    @classmethod
    def find_by_unique_id(cls, unique_id):
        return DBS.query(cls).filter_by(unique_id=unique_id).first()

