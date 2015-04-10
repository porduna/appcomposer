import uuid
import datetime

from flask.ext.login import UserMixin

from sqlalchemy import sql, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relation, backref

from appcomposer.db import db

import base64

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

    composer = db.Column(db.Unicode(50), index=True, nullable=False, server_default=u'expert')
    data = db.Column(db.Text, nullable=False, server_default=u'{}')
    creation_date = db.Column(db.DateTime, nullable=False, index=True)
    modification_date = db.Column(db.DateTime, nullable=False, index=True)
    last_access_date = db.Column(db.DateTime, nullable=False, index=True)
    description = db.Column(db.Unicode(1000), nullable=True)

    # TODO: Find out why these relationships seems to not work sometimes.
    owner_id = db.Column(db.Integer, ForeignKey("Users.id"), nullable=False, index=True)
    owner = relation("User", backref=backref("own_apps", order_by=id, cascade='all,delete'))

    spec_id = db.Column(db.Integer, ForeignKey("Specs.id"))
    spec = relation("Spec", backref="apps")  # declare the relation and place a backref to the apps on the Spec objects.

    # An app can have many bundles (one-to-many).
    bundles = relation("Bundle", backref="app")

    def __repr__(self):
        return self.to_json()

    def __init__(self, name=None, owner=None, composer=None, description=None):
        self.name = name
        self.owner = owner
        self.composer = composer
        self.creation_date = self.modification_date = self.last_access_date = datetime.datetime.now()

        # Generate a not-too-long unique id.
        uid = base64.urlsafe_b64encode(uuid.uuid4().bytes[0:15])
        self.unique_id = uid
        while App.find_by_unique_id(self.unique_id) is not None:
            self.unique_id = base64.urlsafe_b64encode(uuid.uuid4().bytes[0:15])

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


class Spec(db.Model):
    """
    Represents an OpenSocial application. The most significant attribute is the Spec URL,
    which is unique.
    """

    __tablename__ = "Specs"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Unicode(500), nullable=False, unique=True)
    pid = db.Column(db.Unicode(100), nullable=False, unique=True)

    # Translator specs can have a special base bundle which links to a special bundle
    # with the most up-to-date default translation for an App. (By most up-to-date
    # we actually mean, with respect to the other Bundles. Remotely the actual spec XML
    # could still contain newer translations, if it wasn't updated in the composer).
    #spec_id = db.Column(db.Integer, ForeignKey("Bundles.id"), nullable=True)
    #base_bundle = relation("Bundle")

    # TODO: The relationship above currently leads to a circular dependency in SQLAlchemy,
    # that's why it is currently disabled.

    def __init__(self, url):
        self.url = url
        self.pid = self._gen_unique_id()

    def _gen_unique_id(self):
        # Generate a not-too-long unique and permanent id.
        uid = base64.urlsafe_b64encode(uuid.uuid4().bytes[0:15])
        return uid

    def __repr__(self):
        return "Spec(%r, %r, %r)" % (self.id, self.url, self.pid)


class Bundle(db.Model):
    """
    Represents a Bundle, which is a set of messages. Bundles are linked to a language and a target group.
    """
    __tablename__ = "Bundles"

    id = db.Column(db.Integer, primary_key=True)
    lang = db.Column(db.Unicode(15))
    target = db.Column(db.Unicode(30))

    # A bundle can have many messages. (one-to-many).
    messages = relation("Message", backref="bundle")

    # We have a backref to our parent App.
    app_id = db.Column(db.Integer, ForeignKey("Apps.id"))

    def __init__(self, lang, target):
        """
        Creates a new Bundle object.
        :param lang: The language (which is really language_TERRITORY).
        :type lang: str
        :param target: The target group.
        :type target: str
        """
        self.lang = lang
        self.target = target

class Message(db.Model):
    """
    Represents a Message, which is the translation for a specific key within a Bundle.
    """
    __tablename__ = "Messages"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Unicode(500), index = True)
    value = db.Column(db.UnicodeText)  # TODO: Check whether this is the best type for value.

    # Ref to the Bundle we belong to. (many-to-one).
    bundle_id = db.Column(db.Integer, ForeignKey("Bundles.id"))

    def __init__(self, key, value):
        """
        Creates a new message object.
        :param key:
        :param value:
        :return:
        """
        self.key = key
        self.value = value

    def __repr__(self):
        return "%r - %r" % (self.key, self.value)


class RepositoryApp(db.Model):
    __tablename__ = 'RepositoryApps'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.Unicode(200), nullable = False, index = True)
    url = db.Column(db.Unicode(255), unique = True, nullable = False, index = True)
    app_thumb = db.Column(db.Unicode(255))
    description = db.Column(db.UnicodeText)

    repository = db.Column(db.Unicode(400), nullable = False, index = True)
    external_id = db.Column(db.Unicode(200), index = True)

    adaptable = db.Column(db.Boolean, index = True)
    translatable = db.Column(db.Boolean, index = True)

    original_translations = db.Column(db.Unicode(255))

    last_check = db.Column(db.DateTime, index = True)
    last_change = db.Column(db.DateTime, index = True)
    failing = db.Column(db.Boolean, index = True)
    failing_since = db.Column(db.DateTime, index = True)

    def __init__(self, name, url, repository, external_id = None):
        self.name = name
        self.url = url
        self.repository = repository
        self.external_id = unicode(external_id)

        self.app_thumb = None
        self.description = None

        self.adaptable = False
        self.translatable = False
        self.original_translations = ""

        self.last_check = None
        self.last_change = None
        
        self.failing = False
        self.failing_since = None

class GoLabOAuthUser(db.Model):
    __tablename__ = 'GoLabOAuthUsers'

    id = db.Column(db.Integer, primary_key = True)
    display_name = db.Column(db.Unicode(255), index = True, nullable = False)
    email = db.Column(db.Unicode(255), index = True, nullable = False, unique = True)

    def __init__(self, email, display_name):
        self.email = email
        self.display_name = display_name

    def __repr__(self):
        return "GoLabOAuthUsers(%r, %r)" % (self.email, self.display_name)

    def __unicode__(self):
        return u"%s <%s>" % (self.display_name, self.email)


class TranslationUrl(db.Model):
    __tablename__ = 'TranslationUrls'

    id = db.Column(db.Integer, primary_key = True)
    url = db.Column(db.Unicode(255), unique = True, nullable = False, index = True)

    def __init__(self, url):
        self.url = url

class TranslatedApp(db.Model):
    __tablename__ = 'TranslatedApps'

    id = db.Column(db.Integer, primary_key = True)
    translation_url_id = db.Column(db.Integer, ForeignKey('TranslationUrls.id'))
    url = db.Column(db.Unicode(255), unique = True, nullable = False, index = True)

    translation_url = relation("TranslationUrl", backref="apps")

    def __init__(self, url, translation_url):
        self.url = url
        if isinstance(translation_url, basestring):
            raise Exception("TranslationApp requires a TranslationUrl, not a string")

        self.translation_url = translation_url

class TranslationBundle(db.Model):
    __tablename__ = 'TranslationBundles'
    __table_args__ = (UniqueConstraint('translation_url_id', 'language', 'target'), )

    id = db.Column(db.Integer, primary_key = True)
    translation_url_id = db.Column(db.Integer, ForeignKey('TranslationUrls.id'))
    language = db.Column(db.Unicode(20), index = True)
    target = db.Column(db.Unicode(20), index = True)
    translation_url = relation("TranslationUrl", backref="bundles")
    from_developer = db.Column(db.Boolean, index = True)

    def __init__(self, language, target, translation_url, from_developer = False):
        self.language = language
        self.target = target
        if isinstance(translation_url, basestring):
            raise Exception("TranslationBundle requires a TranslationUrl, not a string")
        self.translation_url = translation_url
        self.from_developer = from_developer

class TranslationMessageHistory(db.Model):
    __tablename__ = 'TranslationMessageHistory'

    id = db.Column(db.Integer, primary_key = True)
    bundle_id = db.Column(db.Integer, ForeignKey('TranslationBundles.id'))
    user_id = db.Column(db.Integer, ForeignKey('GoLabOAuthUsers.id'))
    key = db.Column(db.Unicode(255), index = True)
    value = db.Column(db.UnicodeText)
    datetime = db.Column(db.DateTime, index = True)
    parent_translation_id = db.Column(db.Integer, index = True)
    taken_from_default = db.Column(db.Boolean, index = True)

    bundle = relation("TranslationBundle", backref="all_messages")
    user = relation("GoLabOAuthUser", backref = "translation_history")

    def __init__(self, bundle, key, value, user, datetime, parent_translation_id, taken_from_default):
        self.bundle = bundle
        self.key = key
        self.value = value
        self.user = user
        self.datetime = datetime
        self.parent_translation_id = parent_translation_id
        self.taken_from_default = taken_from_default

class ActiveTranslationMessage(db.Model):
    __tablename__ = 'ActiveTranslationMessages'
    __table_args__ = (UniqueConstraint('bundle_id', 'key'), )

    id = db.Column(db.Integer, primary_key = True)
    bundle_id = db.Column(db.Integer, ForeignKey('TranslationBundles.id'))
    key = db.Column(db.Unicode(255), index = True)
    value = db.Column(db.UnicodeText)
    history_id = db.Column(db.Integer, ForeignKey("TranslationMessageHistory.id"))
    taken_from_default = db.Column(db.Boolean, index = True)

    bundle = relation("TranslationBundle", backref="active_messages")
    history = relation("TranslationMessageHistory", backref="active")

    def __init__(self, bundle, key, value, history, taken_from_default):
        self.bundle = bundle
        self.key = key
        self.value = value
        self.history = history
        self.taken_from_default = taken_from_default


class TranslationKeySuggestion(db.Model):
    __tablename__ = 'TranslationKeySuggestions'

    id = db.Column(db.Integer, primary_key = True)
    key = db.Column(db.Unicode(255), index = True)
    language = db.Column(db.Unicode(20), index = True)
    target = db.Column(db.Unicode(20), index = True)
    value = db.Column(db.UnicodeText)
    number = db.Column(db.Integer)

    def __init__(self, key, language, target, value, number):
        self.key = key
        self.language = language
        self.target = target
        self.value = value
        self.number = number

class TranslationValueSuggestion(db.Model):
    __tablename__ = 'TranslationValueSuggestions'

    id = db.Column(db.Integer, primary_key = True)
    human_key = db.Column(db.Unicode(255), index = True)
    language = db.Column(db.Unicode(20), index = True)
    target = db.Column(db.Unicode(20), index = True)
    value = db.Column(db.UnicodeText)
    number = db.Column(db.Integer)

    def __init__(self, human_key, language, target, value, number):
        self.human_key = human_key
        self.language = language
        self.target = target
        self.value = value
        self.number = number

