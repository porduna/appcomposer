import json
from requests import patch
import appcomposer
from appcomposer.appstorage import create_app

import appcomposer.application

from flask import session

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
        appcomposer.app.config['TESTING'] = True
        appcomposer.app.config['CSRF_ENABLED'] = False
        appcomposer.app.config["SECRET_KEY"] = 'secret'
        self.flask_app = appcomposer.app.test_client()

        with self.flask_app:
            print "ABOUTTOLOGIN"
            rvw = self.login("aatestuser", "password")
            rvr = self.login("testuser", "password")

            # import readline # optional, will allow Up/Down/History in the console
            # import code
            # vars = globals().copy()
            # vars.update(locals())
            # shell = code.InteractiveConsole(vars)
            # shell.interact()

            print "LENGTH: %d %d" % (len(rvw.data), len(rvr.data))
            print session

            rv = self.login("testuser", "password")
            print "SESSION: "
            print session

                # from appcomposer.login import current_user
                # print "USER: " + current_user()

    def tearDown(self):
        pass

    def test_create(self):
        with appcomposer.app.test_request_context("/"):
            # appdata = {"spec": "test.xml"}
            # self.app = create_app("TestApp", "dummy", json.dumps(appdata))
            pass

    def core_request(self):
        print "DONE: " + str(self.app.get("/").data)