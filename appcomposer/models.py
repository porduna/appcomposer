import uuid
import datetime

from flask.ext.login import UserMixin

from sqlalchemy import sql, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relation, backref

from appcomposer.db import db

import json


class User(db.Model, UserMixin):
    __tablename__ = 'Users'

    id = db.Column(db.Integer, primary_key=True)

    login = db.Column(db.Unicode(50), unique=True)
    name = db.Column(db.Unicode(50), nullable=False)
    password = db.Column(db.Unicode(50), nullable=False)  # NOT USED!!!
    email = db.Column(db.Unicode(254), nullable=False)
    organization = db.Column(db.Unicode(50))  # Organization and role aren't used either.
    role = db.Column(db.Unicode(50))
    creation_date = db.Column(db.DateTime, nullable=False, index=True)
    last_access_date = db.Column(db.DateTime, nullable=False, index=True)
    auth_system = db.Column(db.Unicode(20), nullable=True)
    auth_data = db.Column(db.Unicode(255), nullable=True)

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
        return cls.query.filter(sql.and_(cls.login == login, cls.password == word)).first()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

class AppVersion(db.Model):
    __tablename__ = 'AppVersions'

    version_id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, ForeignKey("Apps.id"), primary_key=True)
    creation_date = db.Column(db.DateTime, nullable=False, index=True)

    app = relation("App", backref="app_versions")

    def __init__(self, version_id=None, app=None):
        self.version_id = version_id
        self.app = app
        self.creation_date = datetime.datetime.now()


# TODO: Changes to consider:
# - Remove id column
# - Make unique_id primary key
# - Remove owner_id ( I think the "owner" relation covers this already? )
class App(db.Model):
    __tablename__ = 'Apps'
    __table_args__ = (UniqueConstraint('name', 'owner_id'), )

    id = db.Column(db.Integer, primary_key=True)

    unique_id = db.Column(db.Unicode(50), index=True, unique=True)
    name = db.Column(db.Unicode(50), index=True)
    owner_id = db.Column(db.Integer, ForeignKey("Users.id"), nullable=False, index=True)
    composer = db.Column(db.Unicode(50), index=True, nullable=False, server_default=u'expert')
    data = db.Column(db.Text, nullable=False, server_default=u'{}')
    creation_date = db.Column(db.DateTime, nullable=False, index=True)
    modification_date = db.Column(db.DateTime, nullable=False, index=True)
    last_access_date = db.Column(db.DateTime, nullable=False, index=True)
    description = db.Column(db.Unicode(1000), nullable=True)
    spec_url = db.Column(db.Unicode(600), nullable=True)  # URL of the XML spec for the App.

    # TODO: Find out why this relationships seems to not work sometimes.
    owner = relation("User", backref=backref("own_apps", order_by=id, cascade='all,delete'))

    def __repr__(self):
        return self.to_json()

    def __init__(self, name=None, owner=None, composer=None, description=None):
        self.name = name
        self.owner = owner
        self.composer = composer
        self.creation_date = self.modification_date = self.last_access_date = datetime.datetime.now()

        self.unique_id = str(uuid.uuid4())
        while App.find_by_unique_id(self.unique_id) is not None:
            self.unique_id = str(uuid.uuid4())

        self.description = description

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
            "last_access_date": self.last_access_date.__str__(),
            "spec_url": self.spec_url
        }
        return d

    def to_json(self):
        """
        Turns the App into a JSON string.
        """
        return json.dumps(self.to_dict())

    @classmethod
    def find_by_unique_id(cls, unique_id):
        return cls.query.filter_by(unique_id=unique_id).first()


class AppVar(db.Model):
    """
    Stores a variable. A variable is a key:value pair linked to a specific App.
    """

    __tablename__ = 'AppVars'

    var_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(50))
    value = db.Column(db.Unicode(500))

    app_id = db.Column(db.Integer, ForeignKey("Apps.id"), nullable=False)
    app = relation("App", backref=backref("appvars"))

    def __init__(self, name=None, value=None):
        self.value = value
        self.name = name

    def __repr__(self):
        return "AppVar(%r, %r, %r)" % (
            self.app.unique_id, self.name, self.value)

    @classmethod
    def find_by_var_id(cls, var_id):
        return cls.query.filter_by(var_id=var_id).first()


