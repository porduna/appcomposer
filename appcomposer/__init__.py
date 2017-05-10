import os
import sys
import optparse


class ComposerRegister(object):
    def __init__(self, url):
        self.url = url


registry = []

from .application import app
from .login import current_user

assert current_user is not None  # ignore pyflakes
from .db import db, upgrader

assert db is not None  # ignore pyflakes

from flask import render_template


@app.route("/")
def index():
    return render_template('index.html')

@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/contact")
def contact():
    return render_template('contact.html')



def run():
    if not upgrader.check():
        print >> sys.stderr, "Database not upgraded!!! Run:"
        print >> sys.stderr, "  alembic upgrade head"
        print >> sys.stderr, "And then run this script again"
        sys.exit(-1)
    parser = optparse.OptionParser(usage="Run in development mode the App Composer. In production, please use WSGI.")

    parser.add_option('-p', '--port', dest='port', metavar="PORT",
                      help="Port to be used",
                      type='int', default=5000)

    parser.add_option('--testing', dest='testing', help="Enter in testing mode", default=False, action='store_true')

    parser.add_option('--release', dest='release', help="Enter in a release mode", default=False, action="store_true")

    args, _ = parser.parse_args()

    if args.testing:
        app.config['TESTING'] = True
        app.config['CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
    elif args.release:
        app.config["TESTING"] = False
        app.config["CSRF_ENABLED"] = True
        app.config["DEBUG"] = False
    else:
        app.config['DEBUG'] = True
        app.config["CSRF_ENABLED"] = True
        app.config["SECRET_KEY"] = 'secret'

    if app.config['DEBUG']:
        from flask_debugtoolbar import DebugToolbarExtension
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
        app.config['DEBUG_TB_PROFILER_ENABLED'] = False
        toolbar = DebugToolbarExtension(app)

    port = int(os.environ.get('PORT', args.port))
    #print app.url_map
    app.run(host='0.0.0.0', port=port, threaded=True)
