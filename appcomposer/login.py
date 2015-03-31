import json
import string
import random
import datetime
import urllib2
import requests

from hashlib import new as new_hash

from functools import wraps

from flask import session, render_template, flash, request, redirect, url_for
from flask.ext.wtf import TextField, Form, PasswordField, validators

from appcomposer import db
from .models import User

from .application import app
from .babel import gettext, lazy_gettext


def current_user():
    if not session.get("logged_in", False):
        return None

    return User.query.filter_by(login=session['login']).first()


def requires_login(f):
    """
    Require that a particular flask URL requires login. It will require the user to be logged,
    and if he's not logged he will be redirected there afterwards.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return wrapper


class LoginForm(Form):
    login = TextField(lazy_gettext(u"Login:"), validators=[validators.Required()])
    password = PasswordField(lazy_gettext(u"Password:"), validators=[validators.Required()])


def login_user(login, name):
    # Store the username in the session object.
    # The session is stored client-side but cryptographically signed.
    session["logged_in"] = True
    session["login"] = login
    session["name"] = name


def create_salted_password(password):
    alphabet = string.ascii_letters + string.digits
    CHARS = 6
    random_str = ""
    for _ in range(CHARS):
        random_str += random.choice(alphabet)

    salted_password = unicode(new_hash("sha", random_str + password).hexdigest())
    return random_str + "::" + salted_password


def check_salted_password(password, salted_password):
    random_str = salted_password[:6]
    rest = salted_password[8:]
    salted = unicode(new_hash("sha", random_str + password).hexdigest())
    return rest == salted


@app.route('/login', methods=["GET", "POST"])
def login():
    return _login_impl(app.config.get('DEBUG', False))


@app.route('/login-local', methods=["GET", "POST"])
def login_local():
    return _login_impl(True)


def _login_impl(show_local_users):
    next_url = request.args.get('next', '')

    form = LoginForm(request.form)

    login_app = app.config.get('GRAASP_LOGIN_APP', None)
    login_app_creation = app.config.get('SHOW_LOGIN_APP_CREATION', False)

    # If a login app is not provided, show the creation interface
    if not login_app:
        login_app_creation = True


    # This is an effective login request
    if form.validate_on_submit():
        user = User.query.filter_by(login=form.login.data, auth_system="userpass").first()
        if user and check_salted_password(form.password.data, user.auth_data):
            login_user(form.login.data, user.name)
            return redirect(next_url or url_for('user.index'))
        else:
            flash(gettext("Invalid login"))

    return render_template("login/login.html", form=form, next=next_url, login_app=login_app,
                           login_app_creation=login_app_creation, show_local_users=show_local_users)


def login_as(login):
    user = User.query.filter_by(login=login).first()
    if user:
        login_user(login, user.name)
    else:
        flash(gettext("User does not exist"))


@app.route('/logout', methods=["GET", "POST"])
def logout():
    if "logged_in" in session and session["logged_in"]:
        session["logged_in"] = False
        session["login"] = ""
        return redirect(url_for("index"))
    else:
        return redirect(url_for("index"))


@app.route('/graasp-login')
def graasp_login():
    login_app = app.config.get('GRAASP_LOGIN_APP', None)
    login_app_creation = app.config.get('SHOW_LOGIN_APP_CREATION', False)

    # If a login app is not provided, show the creation interface
    if not login_app:
        login_app_creation = True

    return render_template('login/graasp.html', login_app=login_app, login_app_creation=login_app_creation)

PUBLIC_APPCOMPOSER_ID = 'WfTlrXTbu4AeGexikhau5HDXkpGE8RYh'

@app.route('/graasp/oauth/')
def graasp_oauth_login():
    redirect_back_url = url_for('graasp_oauth_login_redirect', _external = True)
    return redirect('http://graasp.eu/authorize?client_id=%s&redirect_uri=%s' % (PUBLIC_APPCOMPOSER_ID, requests.utils.quote(redirect_back_url, '')))

@app.route('/graasp/oauth/redirect/')
def graasp_oauth_login_redirect():
    access_token = request.args.get('access_token')
    refresh_token = request.args.get('refresh_token')
    timeout = request.args.get('expires_in')

    headers = {
        'Authorization': 'Bearer {}'.format(access_token),
    }

    return requests.get('http://graasp.eu/users/me', headers = headers).text

SHINDIG = 'http://shindig2.epfl.ch'


def url_shindig(url):
    return '%s%s' % (SHINDIG, url)


def graasp_user(id):
    return 'graasp_%s' % id


class Role:
    teacher = 'teacher'
    admin = 'administrator'


ROLES = [Role.teacher, Role.admin]


@app.route('/graasp/authn/')
def graasp_authn():
    st = request.args.get('st', '')
    # Step 1: do something with security token (e.g. check who is)
    current_user_str = urllib2.urlopen(url_shindig("/rest/people/@me/@self?st=%s" % st)).read()
    current_user_data = json.loads(current_user_str)

    name = current_user_data['entry'].get('displayName') or 'anonymous'
    user_id = current_user_data['entry'].get('id') or 'no-id'

    if unicode(user_id) in (u'1', u'2', u'no-id'):
        return render_template("login/errors.html", message=gettext("You must be logged in to use the App Composer."),
                               show_graasp_link=True)

    # Step 2: check if the user is in the database.
    existing_user = User.query.filter_by(login=graasp_user(user_id)).first()
    if existing_user is None:
        # Create the user
        new_user = User(login=graasp_user(user_id), name=name, password='', email='', organization='Graasp',
                        role=Role.teacher, creation_date=datetime.datetime.now(),
                        last_access_date=datetime.datetime.now(), auth_system='graasp', auth_data=user_id)
        db.session.add(new_user)
        db.session.commit()

    # Step 3: log in the user
    login_user(graasp_user(user_id), name)

    # Redirect to the main user interface
    return redirect(url_for('user.index'))


@app.route('/login-widget.xml')
def graasp_widget():
    return render_template('login/widget.xml')

