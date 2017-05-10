import pprint
import traceback
import smtplib
from flask import request, current_app
from functools import wraps

def sendmail(subject, body, additional_recipients = None):
    from appcomposer.application import app
    MAIL_TPL = """From: App Composer <%(sender)s>
To: %(recipients)s
Subject: %(subject)s

%(body)s
"""
    smtp_server = app.config.get("SMTP_SERVER")
    from_addr = app.config.get("SENDER_ADDR")
    to_addrs = app.config.get("ADMINS")
    if not smtp_server or not from_addr or not to_addrs:
        return

    to_addrs = list(to_addrs)
    if additional_recipients is not None:
        to_addrs.extend(additional_recipients)

    server = smtplib.SMTP(smtp_server)

    server.sendmail(from_addr, to_addrs, MAIL_TPL % {
                'sender'     : from_addr,
                'recipients' : ', '.join(to_addrs),
                'subject'    : subject,
                'body'       : body.encode('utf8')
        })

def report_error(subject, body = "Error", additional_recipients = None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except:
                environ = pprint.pformat(request.environ)
                message = '{0}:\n\nFunction: {1}\n\nEnvironment:\n\n{2}\n\nStack trace:\n\n{3}'.format(body, f.__name__, environ, traceback.format_exc())
                sendmail(subject, message, additional_recipients = additional_recipients)
                if current_app.debug:
                    print(message)
                return 'Error. Administrator contacted'
        return wrapper
    return decorator

