import os
import base64
import requests
import logging

from functools import wraps

from flask import session, render_template, request, redirect, url_for, jsonify, current_app

from appcomposer import db
from .models import GoLabOAuthUser

from .application import app
from .utils import sendmail

@app.route('/logout', methods=["GET", "POST"])
def logout():
    if "logged_in" in session and session["logged_in"]:
        session["logged_in"] = False
        session["login"] = ""
        return redirect(url_for("index"))
    else:
        return redirect(url_for("index"))

############################################################
# 
# 
#           Go-Lab OAuth system
# 
# 

PUBLIC_APPCOMPOSER_ID = 'WfTlrXTbu4AeGexikhau5HDXkpGE8RYh'

def token_urlsafe(nbytes=None):
    """Taken from Python 2.6"""
    DEFAULT_ENTROPY=16
    tok = os.urandom(nbytes or DEFAULT_ENTROPY)
    return base64.urlsafe_b64encode(tok).strip().replace('=', '').replace('-', '_')

@app.route('/graasp/oauth/')
def graasp_oauth_login():
    next_url = request.args.get('next')
    if next_url is None:
        return "No next= provided"
    session['oauth_next'] = next_url
    redirect_back_url = url_for('graasp_oauth_login_redirect', _external = True)
    state = token_urlsafe()
    session['state'] = state
    return redirect('https://graasp.eu/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&state={state}'.format(client_id=PUBLIC_APPCOMPOSER_ID, redirect_uri=requests.utils.quote(redirect_back_url, ''), state=state))

@app.route('/graasp/oauth/redirect/')
def graasp_oauth_login_redirect():
    code = request.args.get('code', '')
    state = request.args.get('state', '')
    if state != session.get('state'):
        if not current_app.debug:
            # TODO should be testing...
            return "Invalid ?state= value"


    rsession = requests.Session()

    request_data = dict(code=code, grant_type='authorization_code', client_id=PUBLIC_APPCOMPOSER_ID, client_secret=current_app.config.get('APPCOMPOSER_SECRET'))
    r = rsession.post('https://graasp.eu/token', json=request_data)
    result = r.json()

    access_token = result.get('access_token')
    refresh_token = result.get('refresh_token')
    # timeout = request.args.get('expires_in')
    next_url = session.get('oauth_next')

    headers = {
        'Authorization': 'Bearer {}'.format(access_token),
    }

    response = rsession.get('http://graasp.eu/users/me', headers = headers)
    if response.status_code == 500:
        error_msg = "There has been an error trying to log in with access token: %s and refresh_token %s; attempting to go to %s. Response: %s" % (access_token, refresh_token, next_url, response.text)
        app.logger.error(error_msg)
        sendmail("Error logging in", error_msg)
        return render_template("error_login.html")

    try:
        user_data = response.json()
    except ValueError:
        logging.error("Error logging in user with data: %r" % response.text, exc_info = True)
        raise ValueError("Error logging in user with data: %r" % response.text)
    user = db.session.query(GoLabOAuthUser).filter_by(email = user_data['email']).first()
    if user is None:
        user = GoLabOAuthUser(email = user_data['email'], display_name = user_data['username'])
        db.session.add(user)
        db.session.commit()

    session['golab_logged_in'] = True
    session['golab_email'] = user_data['email']

    return redirect(requests.utils.unquote(next_url or ''))


def current_golab_user():
    if not session.get('golab_logged_in', False):
        if app.config.get('DEBUG'):
            if request.referrer and request.referrer.startswith('http://localhost:9000/'):
                return db.session.query(GoLabOAuthUser).first()
            if app.config.get('FAKE_OAUTH') and request.referrer and request.referrer.startswith('http://localhost:5000/'):
                return db.session.query(GoLabOAuthUser).first()

        return None

    return db.session.query(GoLabOAuthUser).filter_by(email = session['golab_email']).first()

def requires_golab_login(f):
    """
    Require that a particular flask URL requires login. It will require the user to be logged,
    and if he's not logged he will be redirected there afterwards.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_golab_user() is None:
            return redirect(url_for('graasp_oauth_login', next=request.url))
        return f(*args, **kwargs)

    return wrapper

def requires_golab_api_login(f):
    """
    Require that a particular flask URL requires login. It will require the user to be logged,
    and if he's not logged he will be redirected there afterwards.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_golab_user() is None:
            return jsonify(error=True, reason="authenticate"), 403
        return f(*args, **kwargs)

    return wrapper

