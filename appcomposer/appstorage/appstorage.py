

from flask import session, render_template, render_template_string

from flask.ext.wtf import TextField, Form, PasswordField, NumberRange, DateTimeField
from flask import request, redirect, url_for, session

from appcomposer.db import db_session

from appcomposer.application import app

@app.route('/appstorage', methods = ["GET", "POST"])
def appstorage():
    return "Hello appstorage"