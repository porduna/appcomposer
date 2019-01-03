import os
import sys
import optparse
import redlock

registry = []

from flask_redis import FlaskRedis

redis_store = FlaskRedis()

# 25 times x 200 ms = 5 seconds trying to acquire, 200 millis each time
rlock = redlock.Redlock([{"host": "localhost", "port": 6379, "db": 0}, ], retry_count=25)

from .application import app
from .db import db, upgrader

redis_store.init_app(app)

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

import appcomposer.old_adapt_jsconfig as oaj
app.register_blueprint(oaj.old_adapt_jsconfig, url_prefix='/composers/adapt/adaptors/jsconfig')

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
        DebugToolbarExtension(app)

    port = int(os.environ.get('PORT', args.port))
    #print app.url_map
    app.run(host='0.0.0.0', port=port, threaded=True)
