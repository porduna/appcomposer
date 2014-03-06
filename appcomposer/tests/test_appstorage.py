import json
from requests import patch
import appcomposer
from appcomposer.appstorage import create_app

import appcomposer.application

class TestAppstorage:

    def login(self, username, password):
        return self.flask_app.post('/login', data=dict(
            login=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.flask_app.get('/logout', follow_redirects=True)

    def setUp(self):
        print "SETTINGUP"
        appcomposer.app.config['DEBUG'] = True
        appcomposer.app.config["SECRET_KEY"] = 'secret'
        self.flask_app = appcomposer.app.test_client()

        print "ABOUTTOLOGIN"
        rv = self.login("testuser", "password")
        print self.flask_app.get("/user/", follow_redirects=True).data

        from flask import session
        print session

        with appcomposer.app.test_request_context("/"):

            from flask import session
            print session

            from appcomposer.login import current_user
            print "USER: " + current_user()

    def tearDown(self):
        pass

    def test_create(self):
        with appcomposer.app.test_request_context("/"):
            appdata = {"spec": "test.xml"}
            self.app = create_app("TestApp", "dummy", json.dumps(appdata))
            pass

    def core_request(self):
        print "DONE: " + str(self.app.get("/").data)