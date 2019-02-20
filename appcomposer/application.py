from logging.handlers import SMTPHandler, RotatingFileHandler
import os
import traceback

from flask import Flask, request
from flask import escape

import logging
import pprint

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(32)
app.config['SESSION_COOKIE_NAME'] = 'appcompsession'
app.config['SQLALCHEMY_NATIVE_UNICODE'] = True
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.from_object('config')

domain_whitelist = app.config.get('SSL_DOMAIN_WHITELIST') or []
# domains that for some reason python requests fail to understand (chain error)
domain_whitelist.append('amrita.olabs.edu.in')
domain_whitelist.append('amrita.olabs.co.in')
domain_whitelist.append('cdac.olabs.edu.in')
domain_whitelist.append('cosci.tw')
app.config['SSL_DOMAIN_WHITELIST'] = domain_whitelist


# Add an extension to jinja2
app.jinja_env.add_extension("jinja2.ext.i18n")

from appcomposer.i18n import Babel

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

    class MailLoggingFilter(logging.Filter):
        def filter(self, record):
            try:
                record.environ = pprint.pformat(request.environ)
            except RuntimeError:
                # This on production will raise an "out of request context" error. We ignore it.
                # TODO: Check if there is some way to detect that we are outside, rather than rely on an exception.
                return False
            try:
                from appcomposer.login import current_golab_user
                from appcomposer import db
                db.session.remove()
                user = current_golab_user()
                if user is None:
                    record.user = 'User not logged in'
                else:
                    record.user = user.email
            except:
                record.user = 'Error checking user'
                traceback.print_exc()
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

        User: %(user)s

        Message:

        %(message)s

        Environment:

        %(environ)s

        Stack Trace:
        ''')
    mail_handler.setFormatter(formatter)
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)


line_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Register the file handler.
if(app.config.get("LOGFILE") is not None):
    file_handler = RotatingFileHandler(app.config.get("LOGFILE"))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(line_formatter)
    app.logger.addHandler(file_handler)

logging_level = app.config.get("APPCOMP_LOGGING_LEVEL", "DEBUG")

# Register the cmd handler.
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging_level)
stream_handler.setFormatter(line_formatter)
app.logger.addHandler(stream_handler)


# This seems to be required for the logging of sub-warning messages to work, though
# it doesn't seem to be mentioned in the flask documentation.
app.logger.setLevel(logging_level)





#####
# Main components
#####

from .views.main import translator_blueprint
app.register_blueprint(translator_blueprint, url_prefix='/translator')

from .views.api import translator_api_blueprint
app.register_blueprint(translator_api_blueprint, url_prefix='/translator/api')

from .views.translations import translations_blueprint_v1
app.register_blueprint(translations_blueprint_v1, url_prefix='/translations/v1')

from .views.stats import translator_stats_blueprint
app.register_blueprint(translator_stats_blueprint, url_prefix='/translator/stats')

from .views.dev import translator_dev_blueprint
app.register_blueprint(translator_dev_blueprint, url_prefix='/translator/dev')

from .graasp_i18n import graasp_i18n_blueprint
app.register_blueprint(graasp_i18n_blueprint, url_prefix='/graasp_i18n')

from .speakup_i18n import speakup_i18n_blueprint
app.register_blueprint(speakup_i18n_blueprint, url_prefix='/speakup_i18n')

from .twente_commons import twente_commons_blueprint
app.register_blueprint(twente_commons_blueprint, url_prefix='/twente_commons')

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

@app.errorhandler(500)
def error500(err):
    return "An internal error occurred. You may try a different action, or contact the administrators.", 500

app.logger.info("Flask App object is ready")
