import os, sys
import optparse
from flask import render_template

class ComposerRegister(object):
    def __init__(self, url):
        self.url = url

registry = []

from .application import app
from .login import current_user
assert current_user is not None # ignore pyflakes
from .db import db_session, upgrader
assert db_session is not None # ignore pyflakes

@app.route("/")
def index():
    return render_template("index.html")

def run():
    if not upgrader.check():
        print >> sys.stderr, "Database not upgraded!!! Run:"
        print >> sys.stderr, "  alembic upgrade head"
        print >> sys.stderr, "And then run this script again"
        sys.exit(-1)
    parser = optparse.OptionParser(usage =  "Run in development mode the App Composer. In production, please use WSGI.")

    parser.add_option('-p', '--port', dest='port', metavar="PORT",
                        help="Port to be used",
                        type='int', default=5000)

    parser.add_option('--testing', dest='testing', help="Enter in testing mode", default=False, action='store_true')

    args, _ = parser.parse_args()

    if args.testing:
        app.config['TESTING'] = True
        app.config['CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
    else:
        app.config['DEBUG'] = True
        app.config["SECRET_KEY"] = 'secret'

    port = int(os.environ.get('PORT', args.port))
    print app.url_map
    app.run(host='0.0.0.0', port=port, threaded = True)
 
