from flask import session, render_template, render_template_string, flash

from flask.ext.wtf import TextField, Form, PasswordField, NumberRange, DateTimeField, validators
from flask import request, redirect, url_for, session

from .db import db_session
from .models import User

from .application import app

def current_user():
    if not session.get("logged_in", False):
        return None
    
    return db_session.query(User).filter_by(login = session['login']).first()
    
class LoginForm(Form):
    login               = TextField(u"Login:", validators = [ validators.Required() ])
    password            = PasswordField(u"Password:", validators = [ validators.Required() ])

@app.route('/login', methods = ["GET", "POST"])
def login():
    next_url = request.args.get('next', '')
    
    form = LoginForm(request.form)
        
    # This is an effective login request
    if form.validate_on_submit():
        num = db_session.query(User).filter_by(login = form.login.data, auth_data = form.password.data).count()
        if num == 0:
            flash("Invalid login")
        else:
            # Store the username in the session object.
            # The session is stored client-side but cryptographically signed.
            session["logged_in"] = True
            session["login"] = form.login.data
            return redirect(next_url or "/user")
        
    return render_template("login/login.html", form=form, next=next_url)


@app.route('/logout', methods = ["GET", "POST"])
def logout():
    if "logged_in" in session and session["logged_in"] == True:
        session["logged_in"] = False
        session["login"] = ""
        return redirect("/")
    else:
        return render_template_string("You are not logged in.")



