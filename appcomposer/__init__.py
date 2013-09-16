import os
import optparse
from flask import render_template

from .application import app

@app.route("/")
def index():
    return render_template("index.html")


def run():
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

    port = int(os.environ.get('PORT', args.port))
    app.run(host='0.0.0.0', port=port, threaded = True)
 
