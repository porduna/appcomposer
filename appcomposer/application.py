import os

from flask import Flask, request, render_template
from flask import escape


app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(32)
app.config['SESSION_COOKIE_NAME'] = 'appcompsession'
app.config['SQLALCHEMY_NATIVE_UNICODE'] = True
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600
app.config.from_object('config')

# Add an extension to jinja2
app.jinja_env.add_extension("jinja2.ext.i18n")

# Support old deployments
if not app.config.get('SQLALCHEMY_DATABASE_URI', False):
    if app.config.get('SQLALCHEMY_ENGINE_STR', False):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_ENGINE_STR']

from appcomposer.babel import Babel

if Babel is None:
    print "Not using Babel. Everything will be in English"
else:
    babel = Babel(app)

    supported_languages = ['en']
    supported_languages.extend([translation.language for translation in babel.list_translations()])

    @babel.localeselector
    def get_locale():
        locale = request.args.get('locale', None)
        if locale is None:
            locale = request.accept_languages.best_match(supported_languages)
        if locale is None:
            locale = 'en'
        return locale


# Initialize the logging mechanism to send error 500 mails to the administrators
if not app.debug and app.config.get("ADMINS") is not None and app.config.get("SMTP_SERVER") is not None:
    import logging
    import pprint
    from logging.handlers import SMTPHandler

    class MailLoggingFilter(logging.Filter):
        def filter(self, record):
            pass
            record.environ = pprint.pformat(request.environ)
            return True

    app.logger.addFilter(MailLoggingFilter())

    smtp_server = app.config.get("SMTP_SERVER")
    from_addr = app.config.get("SENDER_ADDR")
    to_addrs = app.config.get("ADMINS")
    mail_handler = SMTPHandler(smtp_server,
                                from_addr,
                                to_addrs,
                                "AppComposer Application Error Report")
    formatter = logging.Formatter(
        '''
        Message type:       %(levelname)s
        Location:           %(pathname)s:%(lineno)d
        Module:             %(module)s
        Function:           %(funcName)s
        Time:               %(asctime)s

        Message:

        %(message)s

        Environment:

        %(environ)s

        Stack Trace:
        ''')
    mail_handler.setFormatter(formatter)
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)





###
# Composers info
###

ACTIVATE_TRANSLATOR = app.config.get('ACTIVATE_TRANSLATOR', False)

from .composers.dummy import info as dummy_info
from .composers.adapt import info as adapt_info

COMPOSERS = [adapt_info]

if ACTIVATE_TRANSLATOR:
    from .composers.translate import info as translate_info

    COMPOSERS.append(translate_info)

# So that we can have access to all the info from the Users component.
# It is important that this is done early. Otherwise, it will be accessed by the
# user component before it is ready.

COMPOSERS_DICT = {info["blueprint"]: info for info in COMPOSERS}
COMPOSERS_DICT[dummy_info['blueprint']] = dummy_info


def register_dummy():
    COMPOSERS.insert(0, dummy_info)


app.config['COMPOSERS'] = COMPOSERS

# TODO: The COMPOSERS_DICT thing is not very pretty. Find a work-around.


#####
# Main components 
#####

#
# Initialize administration panels
# 

# User component
from .user.user_application import initialize_user_component

initialize_user_component(app)


# Admin component
from .admin.admin_application import initialize_admin_component

initialize_admin_component(app)


#####
# Composers
#####
from .composers.adapt import adapt_blueprint, adaptors_blueprints, load_plugins
from .composers.expert import expert_blueprint
from .composers.dummy import dummy_blueprint

if ACTIVATE_TRANSLATOR:
    from .composers.translate import translate_blueprint

    app.register_blueprint(translate_blueprint, url_prefix='/composers/translate')

app.register_blueprint(adapt_blueprint, url_prefix='/composers/adapt')
load_plugins()
for adaptor_blueprint in adaptors_blueprints:
    app.register_blueprint(adaptor_blueprint)
app.register_blueprint(expert_blueprint, url_prefix='/composers/expert')
app.register_blueprint(dummy_blueprint, url_prefix=dummy_info["url"])


# Mostly for debugging purposes, this snippet will print the site-map so that we can check
# which methods we are routing.
@app.route("/site-map")
def site_map():
    lines = []
    for rule in app.url_map.iter_rules():
        line = str(escape(repr(rule)))
        lines.append(line)

    ret = "<br>".join(lines)
    return ret



@app.route("/error")
def error():
    a = 2/0
    return "ERROR", 404

@app.errorhandler(500)
def error500(err):
    return render_template("composers/errors.html", message="An internal error occurred. You may try a different action, or contact the administrators."), 500


# app.run(debug=False, port=8000)

