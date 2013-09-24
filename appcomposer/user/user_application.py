
from flask import Flask
from flask import redirect, request, flash
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose
from flask.ext.wtf import TextField, Form, PasswordField, NumberRange, DateTimeField
from .fields import DisabledTextField

from appcomposer import db
from appcomposer import models

from sqlalchemy.orm import scoped_session, sessionmaker


class UserApplication(object):
    
    def __init__(self, flask_app):
        self.app = flask_app
        
        # Establish a db session
        self.db_session = db.db_session
        
        
        # Initialize the Admin
        # URL describes through which address we access the page.
        # Endpoint enables us to do url_for('userp') to yield the URL
        self.admin = Admin(self.app, index_view = HomeView(), name = "User Profile", url = "/user", endpoint = "user")
        
        self.admin.add_view(EditView(name='Edit'))
        self.admin.add_view(ProfileEditView(self.db_session, name="Profile"))
        

        
class EditView(BaseView):
    @expose('/')
    def index(self):
        return self.render("user/index.html")
    
    
class HomeView(BaseView):
    
    def __init__(self):
        super(HomeView, self).__init__(endpoint = "user", url = "/user", static_folder="static", static_url_path="/static")
    
    @expose('/')
    def index(self):
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

class ProfileEditView(BaseView):

    def __init__(self, db_session, *args, **kwargs):
        super(ProfileEditView, self).__init__(*args, **kwargs)
        self._session = db_session

    @expose(methods=['GET','POST'])
    def index(self):
        """
        index(self)
        
        This method will be invoked for the Profile Edit view. This view is used for both viewing and updating
        the user profile. It exposes both GET and POST, for viewing and updating respectively.
        """
        
        # At the moment of writing this login is not supported. For testing purposes, we force it to
        # load a "testuser". If this user doesn't exist the code may not work as intended, though
        # it will try to load test data.
        login = "testuser"
        
        user_list = self._session.query(models.User).filter_by(login = login).all()
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
            self._session.add(user)
            self._session.commit()

        return self.render("user/profile-edit.html", form=form)
    
