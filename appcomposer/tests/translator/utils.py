from flask.ext.testing import TestCase
import appcomposer
from appcomposer import db, app

class BasicTest(TestCase):
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    TESTING = True

    def create_app(self):
        app.config.from_object('appcomposer.tests.translator.utils.BasicTest')
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
