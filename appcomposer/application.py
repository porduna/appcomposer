from flask import Flask
from flask import render_template, render_template_string
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(32)

#####
# Main components 
#####

from .user.user_application import initialize_user_component
from .admin import admin_blueprint

# User component
initialize_user_component(app)

app.register_blueprint(admin_blueprint,     url_prefix = '/admin')


#####
# Composers
#####

from .composers.translate import translate_blueprint
from .composers.adapt     import adapt_blueprint
from .composers.expert    import expert_blueprint

app.register_blueprint(translate_blueprint, url_prefix = '/composers/translate')
app.register_blueprint(adapt_blueprint,     url_prefix = '/composers/adapt')
app.register_blueprint(expert_blueprint,    url_prefix = '/composers/expert')




# This should be moved somewhere else. Meanwhile, I place it here for testing/development purposes.
from flask.ext.wtf import TextField, Form, PasswordField, NumberRange, DateTimeField
from flask import request, redirect, url_for, session
import db
import models

class LoginForm(Form):
    login               = TextField(u"Login:")
    password            = PasswordField(u"Password:")

@app.route('/login', methods = ["GET", "POST"])
def login():
    
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
        num = db.db_session.query(models.User).filter_by(login = form.login.data, auth_data = form.password.data).count()
        if(num == 0):
            return "Wrong user or password"
        else:
            # Store the username in the session object.
            # The session is stored client-side but cryptographically signed.
            session["logged_in"] = True
            session["login"] = form.login.data
            return redirect("/user")
        
        
    return render_template("login/login.html", form=form)

@app.route('/logout', methods = ["GET", "POST"])
def logout():
    if "logged_in" in session and session["logged_in"] == True:
        session["logged_in"] = False
        session["login"] = ""
        return redirect("/")
    else:
        return render_template_string("You are not logged in.")



