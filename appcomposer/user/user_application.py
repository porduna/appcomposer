
from flask import Flask
from flask import redirect, request, flash, session, render_template_string
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose
from flask.ext.wtf import TextField, Form, PasswordField, NumberRange, DateTimeField
from .fields import DisabledTextField

from appcomposer.db import db_session
from appcomposer import models

from sqlalchemy.orm import scoped_session, sessionmaker


def initialize_user_component(app):
    # Initialize the Admin
    # URL describes through which address we access the page.
    # Endpoint enables us to do url_for('userp') to yield the URL
    admin = Admin(app, index_view = HomeView(), name = "User Profile", url = "/user", endpoint = "user")
    admin.add_view(ProfileEditView(name="Profile"))

        
class EditView(BaseView):
    @expose('/')
    def index(self):
        return self.render("user/index.html")
    
    
class HomeView(BaseView):
    
    def __init__(self):
        super(HomeView, self).__init__(endpoint = "user", url = "/user", static_folder="static", static_url_path="/static")
    
    @expose('/')
    def index(self):
        if "logged_in" not in session or session["logged_in"] != True:
            return render_template_string('You are not logged in. You may login <a href="../login">here</a>.')
        
        return self.render('user/index.html')
    
    
class ProfileEditForm(Form):
    name                = DisabledTextField(u"Name:")
    login               = DisabledTextField(u"Login:")
    email               = TextField(u"E-mail:")
    #facebook    = TextField(u"Facebook id:", description="Facebook identifier (number).", validators = [NumberRange(min=1000) ])
    password            = PasswordField(u"Password:", description="Password.")
    organization        = TextField(u"Organization:")
    role                = TextField(u"Role:")
    creation_date       = DisabledTextField(u"Creation date:")
    last_access_date    = DisabledTextField(u"Last access:")
    auth_system         = TextField(u"Auth system:")

class ProfileEditView(BaseView):

    def __init__(self, *args, **kwargs):
        super(ProfileEditView, self).__init__(*args, **kwargs)

    @expose(methods=['GET','POST'])
    def index(self):
        """
        index(self)
        
        This method will be invoked for the Profile Edit view. This view is used for both viewing and updating
        the user profile. It exposes both GET and POST, for viewing and updating respectively.
        """
        
        if "logged_in" not in session or session["logged_in"] != True:
            return render_template_string('You are not logged in. You may login <a href="../login">here</a>.')
        
        login = session["login"]
        
        # This will be passed as a template parameter to let us change the password.
        # (And display the appropriate form field).
        change_password = True
        
        user_list = db_session.query(models.User).filter_by(login = login).all()
        if(len(user_list) > 0):
            user = user_list[0]
        
        
        # If it is a POST request to edit the form, then request.form will not be None
        # Otherwise we will simply load the form data from the DB
        if len(request.form):
            form = ProfileEditForm(request.form, csrf_enabled = True)
        elif len(user_list) == 0:
            form = ProfileEditForm(csrf_enabled = True)
            form.name.data = "no-user" # TODO: Change form item name
            form.login.data = "test"
            form.email.data = "mail@dotcom"
            form.organization.data = "AppComposer"
            form.role.data = "Developer"
            form.creation_date.data = "2013-09-23 14:20:00"
            form.last_access_date.data = "2013-09-23 14:20:00"
            form.auth_system.data = "userpass"
            form.password.data = "password"
        else:
            # It was a GET request (just viewing). 
            form = ProfileEditForm(csrf_enabled = True)
            form.name.data = user.name
            form.login.data = user.login
            form.email.data = user.email
            form.organization.data = user.organization
            form.role.data = user.role
            form.creation_date.data = user.creation_date
            form.last_access_date.data = user.last_access_date
            form.auth_system.data = user.auth_system
            form.password.data = user.auth_data
            
        # If the method is POST we assume that we want to update and not just view
        # TODO: Make sure this is the proper way of handling that. The main purpose here
        # is to avoid carrying out a database commit if it isn't needed.
        if request.method == "POST" and form.validate_on_submit():
            # It was a POST request, the data (which has been modified) will be contained in
            # the request. For security reasons, we manually modify the user for these
            # settings which should actually be modifiable.
            user.email = form.email.data
            user.organization = form.organization.data
            user.role = form.role.data
            user.auth_type = form.auth_system.data # Probably in the release we shouldn't let users modify the auth this way
            user.auth_data = form.password.data # For the userpass method, the auth_data should contain the password. Eventually, should add hashing.
            db_session.add(user)
            db_session.commit()

        return self.render("user/profile-edit.html", form=form, change_password=change_password)
    
