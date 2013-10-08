from flask import session, render_template, render_template_string

from flask.ext.wtf import TextField, Form, PasswordField, NumberRange, DateTimeField
from flask import request, redirect, url_for, session

from .db import db_session
from .models import User

from .application import app

def current_user():
    if not session.get("logged_in", False):
        return None
    
    return db_session.query(User).filter_by(login = session['login']).first()
    
class LoginForm(Form):
    login               = TextField(u"Login:")
    password            = PasswordField(u"Password:")

@app.route('/login', methods = ["GET", "POST"])
def login():

    next_url = request.args.get('next', '')
    
    if len(request.form):
        # We probably got here from a POST
        form = LoginForm(request.form, csrf_enabled = True)
    else:
        # We probably got here through a GET
        form = LoginForm()
        form.login.data = ""
        form.password.data = "TestPassword"
        
    # This is an effective login request
    if request.method == "POST":
        num = db_session.query(User).filter_by(login = form.login.data, auth_data = form.password.data).count()
        if(num == 0):
            return "Wrong user or password"
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



