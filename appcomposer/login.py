import json
import urllib

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


@app.route('/login', methods=["GET", "POST"])
def login():
    next_url = request.args.get('next', '')

    form = LoginForm(request.form)

    # This is an effective login request
    if form.validate_on_submit():
        num = db_session.query(User).filter_by(login=form.login.data, auth_data=form.password.data).count()
        if num == 0:
            flash("Invalid login")
        else:
            # Store the username in the session object.
            # The session is stored client-side but cryptographically signed.
            session["logged_in"] = True
            session["login"] = form.login.data
            return redirect(next_url or "/user")

    return render_template("login/login.html", form=form, next=next_url)


@app.route('/logout', methods=["GET", "POST"])
def logout():
    if "logged_in" in session and session["logged_in"]:
        session["logged_in"] = False
        session["login"] = ""
        return redirect("/")
    else:
        return render_template_string("You are not logged in.")

@app.route('/graasp-login')
def graasp_login():
    origin_url = url_for('graasp_login', _external = True)
    widget_url = url_for('graasp_widget', _external = True)

    data = {
        "url": origin_url,
        "phases": [
            {
                "items": [
                    {
                        "url": widget_url,
                        "name": "Login app",
                        "description": "Login app for App composer"
                    },
                ],
                "name": "Login",
                "description": "You may log in the app composer from here."
            }
        ],
        "name": "App Composer log in space",
        "description": "<p>In this space, you may log in the app composer automatically</p>\n"
    }

    url_base = "https://graasp.epfl.ch/spaces/instantiate/ils.json?ils="

    space_creation_link = url_base + urllib.quote(json.dumps(data))
    return render_template('login/graasp.html', space_creation_link = space_creation_link)

@app.route('/graasp/authn/')
def graasp_authn():
    security_token = request.args.get('st', '')
    # Step 1: do something with security token (e.g. check who is)
    # Step 2: check if the user is in the database. If it is, log him in.
    # Step 3: if he is not in the database, create the user. And then log him in.
    return ":-)"

@app.route('/login-widget.xml')
def graasp_widget():
    return render_template('login/widget.xml')

