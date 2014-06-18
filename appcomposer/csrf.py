"""
Custom CSRF protection scheme.

FROM TEMPLATES:
* csrf_field() creates a full hidden field.
* csrf_token() creates (only) the csrf token from anywhere.

FROM CODE:
* verify_csrf(request) verifies that a request includes the
  right CSRF code.
"""

import uuid

from .application import app as flask_app
from flask import session


def generate_csrf_token():
    """
    Generate a CSRF code.
    """
    if '_csrf_token' not in session:
        session['_csrf_token'] = uuid.uuid1().get_hex()
    return session['_csrf_token']


def generate_csrf_hidden_field():
    """
    Generates a full hidden field with its CSRF protection.
    """
    str = '<input type="hidden" name="_csrf_token" value="%s"/>' % generate_csrf_token()
    return str


def verify_csrf(request):
    """
    Verifies that the specified request has a csrf token which matches the session's.
    If CSRF is disabled on the flask config it returns TRUE without checking.

    @param request: The request to verify.
    @return: True if the CSRF matches, False otherwise.
    """
    enabled = flask_app.config.get("CSRF_ENABLED")
    if not enabled or enabled == False:
        print "[Warning]: CSRF check bypassed"
        return True
    token = session.pop("_csrf_token", None)
    if not token or token != request.values.get("_csrf_token"):
        return False
    return True


def verify_ajax_csrf(request):
    """
    Verifies that the specified request contains a X-CSRF HTTP header with a csrf token
    which matches the session's. If CSRF is disabled on the flask config it returns TRUE
    without checking.

    @param request: The request to verify.
    @return: True if the CSRF matches, False otherwise.
    """
    enabled = flask_app.config.get("CSRF_ENABLED")
    if not enabled or enabled == False:
        print "[Warning]: CSRF check bypassed"
        return True
    # token = session.pop("_csrf_token", None)
    token = session.get("_csrf_token", None)
    if not token or token != request.headers.get("x-csrf"):
        return False
    return True


@flask_app.context_processor
def register_jinja_csrf_globals():
    """
    Adds the csrf_token and csrf_field methods to Jinja.
    """
    return dict(csrf_token=generate_csrf_token, csrf_field=generate_csrf_hidden_field)
