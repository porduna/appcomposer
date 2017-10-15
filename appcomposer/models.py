import hashlib
import datetime

from flask_login import UserMixin

from sqlalchemy import sql, UniqueConstraint, ForeignKey, Index
from sqlalchemy.orm import relation, backref

from appcomposer.db import db

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

    # TODO: Find out why these relationships seems to not work sometimes.
    owner_id = db.Column(db.Integer, ForeignKey("Users.id"), nullable=False, index=True)
    owner = relation("User", backref=backref("own_apps", order_by=id, cascade='all,delete'))

class Language(db.Model):
    __tablename__ = 'Languages'

    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.Unicode(10), index=True, unique=True)

    def __init__(self, language):
        self.language = language

class RepositoryApp(db.Model):
    __tablename__ = 'RepositoryApps'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.Unicode(200), nullable = False, index = True)
    url = db.Column(db.Unicode(1024), nullable = False)
    app_thumb = db.Column(db.Unicode(255))
    description = db.Column(db.UnicodeText)
    app_link = db.Column(db.Unicode(255))
    app_image = db.Column(db.Unicode(255))

    repository = db.Column(db.Unicode(400), nullable = False, index = True)
    external_id = db.Column(db.Unicode(200), index = True)

    adaptable = db.Column(db.Boolean, index = True)
    translatable = db.Column(db.Boolean, index = True)

    translation_percent = db.Column(db.UnicodeText) # JSON document containing which bundles have been translated how much

    last_check = db.Column(db.DateTime, index = True)
    last_change = db.Column(db.DateTime, index = True)
    last_download_change = db.Column(db.DateTime, index = True)
    failing = db.Column(db.Boolean, index = True)
    failing_since = db.Column(db.DateTime, index = True)

    supports_ssl = db.Column(db.Boolean, index=True)
    contains_flash = db.Column(db.Boolean, index=True)

    downloaded_hash = db.Column(db.Unicode(255), index=True)
    contents_hash = db.Column(db.Unicode(255), index=True)
    last_processed_downloaded_hash = db.Column(db.Unicode(255), index=True)
    last_processed_contents_hash = db.Column(db.Unicode(255), index=True)
    last_processed_time = db.Column(db.DateTime, index=True)

    def __init__(self, name, url, repository, external_id = None):
        self.name = name
        self.url = url
        self.repository = repository
        self.external_id = unicode(external_id)

        self.app_thumb = None
        self.description = None

        self.adaptable = False
        self.translatable = False

        self.last_check = None
        self.last_change = None
        
        self.failing = False
        self.failing_since = None

    @property
    def original_translations(self):
        return ','.join([ ote.language.language for ote in self.languages ])

    @original_translations.setter
    def original_translations(self, attr):
        if not attr:
            return

        languages = list(attr.split(','))
        if not languages:
            return

        for orig_lang in self.original_translations.split(','):
            if orig_lang in languages:
                languages.remove(orig_lang)

        for lang_db in db.session.query(Language).filter(Language.language.in_(languages)).all():
            new_lang = RepositoryAppLanguage(repository_app=self, language=lang_db)
            db.session.add(new_lang)

Index('ix_RepositoryApps_url_shortened', RepositoryApp.url, mysql_length={'url': 255})

class RepositoryAppCheckUrl(db.Model):
    __tablename__ = 'RepositoryAppCheckUrls'
    __table_args__ = (UniqueConstraint('repository_app_id', 'url_hash'), )

    id = db.Column(db.Integer, primary_key=True)
    repository_app_id = db.Column(db.Integer, db.ForeignKey('RepositoryApps.id'), nullable=False)
    url = db.Column(db.Unicode(1024), nullable=False) # not index=true; Index below
    url_hash = db.Column(db.Unicode(255), nullable=False, index=True)
    supports_ssl = db.Column(db.Boolean, index=True)
    working = db.Column(db.Boolean, index=True)
    contains_flash = db.Column(db.Boolean, index=True)
    last_update = db.Column(db.DateTime, index=True)

    repository_app = db.relation("RepositoryApp", backref="check_urls")

    def __init__(self, repository_app, url):
        self.repository_app = repository_app
        self.url = url
        self.url_hash = hashlib.md5(url.encode('utf8')).hexdigest()
        self.supports_ssl = None
        self.working = None
        self.contains_flash = None
        self.last_update = datetime.datetime.utcnow()

    def update(self):
        self.last_update = datetime.datetime.utcnow()

Index('ix_RepositoryAppCheckUrls_url_shortened', RepositoryAppCheckUrl.url, mysql_length={'url': 255})

class RepositoryAppFailure(db.Model):
    __tablename__ = 'RepositoryAppFailures'

    id = db.Column(db.Integer, primary_key=True)

    repository_app_check_url_id = db.Column(db.Integer, db.ForeignKey('RepositoryAppCheckUrls.id'))

    current = db.Column(db.Boolean, index=True)
    started = db.Column(db.DateTime, index=True)
    ended = db.Column(db.DateTime, index=True)

    repository_app_check_url = db.relation("RepositoryAppFailure", backref="failures")

    def __init__(self, app_checker_url):
        self.current = True
        self.started = datetime.datetime.utcnow()
        self.repository_app_check_url = app_check_url

    def finished(self):
        self.current = False
        self.ended = datetime.datetime.utcnow()


class RepositoryAppLanguage(db.Model):

    __tablename__ = 'RepositoryApp2languages'
    __table_args__ = (UniqueConstraint('repository_app_id', 'language_id'), )
    
    repository_app_id = db.Column(db.Integer, db.ForeignKey('RepositoryApps.id'), primary_key=True)
    language_id = db.Column(db.Integer, db.ForeignKey('Languages.id'), primary_key=True)

    language = db.relation("Language", backref="repository_apps")
    repository_app = db.relation("RepositoryApp", backref="languages")
    
    def __init__(self, repository_app, language):
        self.repository_app = repository_app
        self.language = language

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
    automatic = db.Column(db.Boolean, index = True)
    attribs = db.Column(db.UnicodeText)

    def __init__(self, url, automatic = True, attribs = ''):
        self.url = url
        self.automatic = automatic
        self.attribs = attribs

    def __unicode__(self):
        return self.url

class TranslationNotificationRecipient(db.Model):
    __tablename__ = 'TranslationNotificationRecipients'

    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.Unicode(255), unique = True, nullable = False, index = True)
    created = db.Column(db.DateTime, index = True)

    def __init__(self, email):
        self.email = email
        self.created = datetime.datetime.utcnow()

class TranslationSubscription(db.Model):
    __tablename__ = 'TranslationSubscriptions'

    id = db.Column(db.Integer, primary_key = True)
    translation_url_id = db.Column(db.Integer, ForeignKey('TranslationUrls.id'))
    recipient_id = db.Column(db.Integer, ForeignKey('TranslationNotificationRecipients.id'))
    mechanism = db.Column(db.Unicode(255), nullable = False, index = True)
    last_check = db.Column(db.DateTime, index = True)
    # mechanism: web, file (...)

    translation_url = relation("TranslationUrl", backref="subscriptions")
    recipient = relation("TranslationNotificationRecipient", backref="subscriptions")

    def __init__(self, translation_url, recipient, mechanism):
        self.translation_url = translation_url
        self.recipient = recipient
        self.mechanism = mechanism
        self.last_check = datetime.datetime.utcnow() - datetime.timedelta(hours = 24)

    def update(self):
        self.last_check = datetime.datetime.utcnow()

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

    def __unicode__(self):
        return self.url

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
    same_tool = db.Column(db.Boolean, index = True)
    tool_id = db.Column(db.Unicode(255), index = True)
    fmt = db.Column(db.Unicode(255), index = True)
    position = db.Column(db.Integer, index = True) # position in the XML file, starting by 0
    category = db.Column(db.Unicode(255), index = True) # optional category for each translation
    from_developer = db.Column(db.Boolean, index = True) # a from_developer bundle can contain some messages which are not from the developer
    namespace = db.Column(db.Unicode(255), index = True) # optional namespace for each translation

    bundle = relation("TranslationBundle", backref="all_messages")
    user = relation("GoLabOAuthUser", backref = "translation_history")

    def __init__(self, bundle, key, value, user, datetime, parent_translation_id, taken_from_default, same_tool, tool_id, fmt, position, category, from_developer, namespace):
        self.bundle = bundle
        self.key = key
        self.value = value
        self.user = user
        self.datetime = datetime
        self.parent_translation_id = parent_translation_id
        self.taken_from_default = taken_from_default
        self.tool_id = tool_id
        self.fmt = fmt
        self.position = position
        self.category = category
        self.from_developer = from_developer
        self.namespace = namespace

class ActiveTranslationMessage(db.Model):
    __tablename__ = 'ActiveTranslationMessages'
    __table_args__ = (UniqueConstraint('bundle_id', 'key'), )

    id = db.Column(db.Integer, primary_key = True)
    bundle_id = db.Column(db.Integer, ForeignKey('TranslationBundles.id'))
    key = db.Column(db.Unicode(255), index = True)
    value = db.Column(db.UnicodeText)
    datetime = db.Column(db.DateTime, index = True)
    history_id = db.Column(db.Integer, ForeignKey("TranslationMessageHistory.id"))
    taken_from_default = db.Column(db.Boolean, index = True)
    same_tool = db.Column(db.Boolean, index = True)
    tool_id = db.Column(db.Unicode(255), index = True)
    fmt = db.Column(db.Unicode(255), index = True)
    position = db.Column(db.Integer, index = True) # position in the XML file, starting by 0
    category = db.Column(db.Unicode(255), index = True) # optional category for each translation
    from_developer = db.Column(db.Boolean, index = True) # a from_developer bundle can contain some messages which are not from the developer
    namespace = db.Column(db.Unicode(255), index = True) # optional namespace for each translation

    bundle = relation("TranslationBundle", backref="active_messages")
    history = relation("TranslationMessageHistory", backref="active")

    def __init__(self, bundle, key, value, history, datetime, taken_from_default, position, category, from_developer, namespace, tool_id, same_tool, fmt):
        if value is None:
            value = ""
        self.bundle = bundle
        self.key = key
        self.value = value
        self.history = history
        self.datetime = datetime
        self.taken_from_default = taken_from_default
        self.position = position
        self.category = category
        self.from_developer = from_developer
        self.namespace = namespace
        self.tool_id = tool_id
        self.same_tool = same_tool
        self.fmt = fmt
        if self.namespace and not self.category:
            self.category = self.namespace


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

class TranslationExternalSuggestion(db.Model):
    __tablename__ = 'TranslationExternalSuggestions'
    __table_args__ = (UniqueConstraint('engine', 'human_key_hash', 'language'), )

    id = db.Column(db.Integer, primary_key = True)
    engine = db.Column(db.Unicode(20), index = True)
    human_key = db.Column(db.Unicode(255), index = True)
    # In MySQL, 'hello' and 'Hello' are equivalent. This causes uniqueness errors
    human_key_hash = db.Column(db.Unicode(36), index = True)
    language = db.Column(db.Unicode(255), index = True)
    origin_language = db.Column(db.Unicode(20), index = True)
    value = db.Column(db.UnicodeText)
    created = db.Column(db.DateTime)

    def __init__(self, engine, human_key, language, origin_language, value):
        self.engine = engine
        self.human_key = human_key[:255]
        self.human_key_hash = hashlib.md5(human_key.encode('utf8')).hexdigest()
        self.language = language
        self.origin_language = origin_language
        self.value = value
        self.created = datetime.datetime.utcnow()


class TranslationSyncLog(db.Model):
    __tablename__ = 'TranslationSyncLogs'

    id = db.Column(db.Integer, primary_key = True)
    start_datetime = db.Column(db.DateTime, index = True)
    end_datetime = db.Column(db.DateTime, index = True)
    source = db.Column(db.Unicode(200))
    cached = db.Column(db.Boolean)
    single_url = db.Column(db.Unicode(255))
    number_apps = db.Column(db.Integer)

    def __init__(self, start_datetime, end_datetime, source, cached, single_url):
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self.source = source
        self.cached = cached
        self.single_url = single_url

class TranslationCurrentActiveUser(db.Model):
    __tablename__ = 'TranslationCurrentActiveUsers'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, ForeignKey('GoLabOAuthUsers.id'))
    bundle_id = db.Column(db.Integer, ForeignKey('TranslationBundles.id'))
    last_check = db.Column(db.DateTime, index = True)

    user = relation("GoLabOAuthUser", backref="realtime_translations")
    bundle = relation("TranslationBundle", backref="realtime_translations")

    def __init__(self, user, bundle, last_check = None):
        self.user = user
        self.bundle = bundle
        if last_check is None:
            self.last_check = datetime.datetime.utcnow()
        else:
            self.last_check = last_check

    def update_last_check(self):
        self.last_check = datetime.datetime.utcnow()


