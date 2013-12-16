import json
import datetime
import urllib
import urllib2

from flask import session, render_template, render_template_string, flash

from flask.ext.wtf import TextField, Form, PasswordField, NumberRange, DateTimeField, validators
from flask import request, redirect, url_for, session

from .db import db_session
from .models import User

from .application import app


def current_user():
    if not session.get("logged_in", False):
        return None

    return db_session.query(User).filter_by(login=session['login']).first()


class LoginForm(Form):
    login = TextField(u"Login:", validators=[validators.Required()])
    password = PasswordField(u"Password:", validators=[validators.Required()])


def login_user(login, name):
    # Store the username in the session object.
    # The session is stored client-side but cryptographically signed.
    session["logged_in"] = True
    session["login"] = login
    session["name"] = name
   

@app.route('/login', methods=["GET", "POST"])
def login():
    next_url = request.args.get('next', '')

    form = LoginForm(request.form)

    # This is an effective login request
    if form.validate_on_submit():
        user = db_session.query(User).filter_by(login=form.login.data, auth_data=form.password.data).first()
        if user is None:
            flash("Invalid login")
        else:
            login_user(form.login.data, user.name)
            return redirect(next_url or url_for('user.index'))

    return render_template("login/login.html", form=form, next=next_url)


@app.route('/logout', methods=["GET", "POST"])
def logout():
    if "logged_in" in session and session["logged_in"]:
        session["logged_in"] = False
        session["login"] = ""
        return redirect(url_for("index"))
    else:
        return render_template_string("You are not logged in.")

@app.route('/graasp-login')
def graasp_login():
    login_app = app.config.get('GRAASP_LOGIN_APP', None)
    login_app_creation = app.config.get('SHOW_LOGIN_APP_CREATION', False)

    # If a login app is not provided, show the creation interface
    if not login_app:
        login_app_creation = True

    return render_template('login/graasp.html', login_app = login_app, login_app_creation = login_app_creation)

SHINDIG = 'https://shindig.epfl.ch'
def url_shindig(url):
    return '%s%s' % (SHINDIG, url)

def graasp_user(id):
    return 'graasp_%s' % id

@app.route('/graasp/authn/')
def graasp_authn():
    st = request.args.get('st', '')
    # Step 1: do something with security token (e.g. check who is)
    current_user_str  = urllib2.urlopen(url_shindig("/rest/people/@me/@self?st=%s" % st)).read()
    current_user_data = json.loads(current_user_str)

    name    = current_user_data['entry'].get('displayName') or 'anonymous'
    user_id = current_user_data['entry'].get('id') or 'no-id'

    # TODO: if user_id == '2', 'no_id'...: error
    if unicode(user_id) in (u'1', u'2', u'no-id'):
        return render_template("login/errors.html", message = "You must be logged in to use the App Composer.")

    # Step 2: check if the user is in the database.
    existing_user = db_session.query(User).filter_by(login=graasp_user(user_id)).first()
    if existing_user is None:
        # Create the user
        new_user = User(login = graasp_user(user_id), name = name, password = '', email = '', organization = 'Graasp', role = '', creation_date = datetime.datetime.now(), last_access_date = datetime.datetime.now(), auth_system = 'graasp', auth_data = user_id)
        db_session.add(new_user)
        db_session.commit()
    
    # Step 3: log in the user
    login_user(graasp_user(user_id), name)

    # Redirect to the main user interface
    return redirect(url_for('user.index'))

@app.route('/login-widget.xml')
def graasp_widget():
    return render_template('login/widget.xml')

