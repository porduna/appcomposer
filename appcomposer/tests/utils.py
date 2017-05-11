import datetime
from flask.ext.testing import TestCase
from appcomposer import db, app
from appcomposer.models import User

class ComposerTest(TestCase):
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

    def create_app(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'secret'
        return app

    def setUp(self):
        db.create_all()
        user = User(login="testuser", name="Test User", password="password", email="no-reply@go-lab-project.eu", role="administrator", auth_system="userpass", auth_data="aaaaaa::72bd124140a0635122771e58a2c79803bbc92a21", creation_date=datetime.datetime.now(), last_access_date=datetime.datetime.now())
        db.session.add(user)
        db.session.commit()

        if hasattr(self, '_cleanup'):
            self._cleanup()

        self.client.__enter__()

    def tearDown(self):
        try:
            if hasattr(self, '_cleanup'):
                self._cleanup()
        finally:
            try:
                self.client.__exit__(None, None, None)
            finally:
                db.session.remove()
                db.drop_all()


    def login(self, username = 'testuser', password = 'password', redirect = True):
        return self.client.post('/login', data=dict(
            login=username,
            password=password
        ), follow_redirects=redirect)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

class LoggedInComposerTest(ComposerTest):
    def setUp(self):
        super(LoggedInComposerTest, self).setUp()
        self.login()

class AppCreatedComposerTest(LoggedInComposerTest):
    def setUp(self):
        from appcomposer.appstorage import api
        super(AppCreatedComposerTest, self).setUp()
        try:
            self.tapp = api.create_app("UTApp", "dummy", None, "{}")
        except:
            self.tearDown()
            raise
