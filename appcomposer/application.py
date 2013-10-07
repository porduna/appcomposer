from flask import Flask
<<<<<<< HEAD
from flask import render_template, render_template_string
import os
=======
from flask import escape
>>>>>>> cc3c3a72b07738f16918c3c9b71a057c48857120

app = Flask(__name__)

# Configure flask app
app.config["DEBUG"] = True
app.config["SECRET_KEY"] = os.urandom(32)

#####
# Main components 
#####

from .user.user_application import UserApplication
from .admin import admin_blueprint

# User component
userApp = UserApplication(app)

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




<<<<<<< HEAD
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



=======

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
>>>>>>> cc3c3a72b07738f16918c3c9b71a057c48857120
