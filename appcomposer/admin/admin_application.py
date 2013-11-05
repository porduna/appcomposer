from flask import redirect, request, flash, session, render_template_string, url_for
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose
from flask.ext.admin.contrib.sqlamodel import ModelView

from flask.ext import wtf
from wtforms.fields import PasswordField

from appcomposer import models
from appcomposer.login import current_user
from appcomposer.db import db_session


##########################################################
#
# Initialization
# 

def initialize_admin_component(app):
    # Initialize the Admin
    # URL describes through which address we access the page.
    # Endpoint enables us to do url_for('userp') to yield the URL
    url = '/admin'
    admin = Admin(index_view = AdminView(url = url, endpoint = 'admin'), name='Admin Profile', endpoint = "home-admin", base_template = 'user/base.html')
    admin.add_view(UsersView(db_session, name='Users', url = 'users', endpoint = 'admin.users'))
    admin.add_view(ApplicationsView(name='Applications', url = 'applications', endpoint = 'admin.applications'))    
    admin.add_view(ProfileView(name='My Profile', url = 'profile', endpoint = 'admin.profile'))    
    admin.init_app(app)


#####################################################################
#
#
# Parent views
#
# 

class MyAdminIndexView(AdminIndexView):
    """
    View that will be used as index for Admin.
    """

    def is_accessible(self):
        self._current_user = current_user()
        return self._current_user is not None

    def _handle_view(self, *args, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('login', next=request.url))
        
        # Just call parent class with predefined model
        return super(MyAdminIndexView, self)._handle_view(*args, **kwargs)


class AdminBaseView(BaseView):
    """
    View that will be used as base for some Admin views (with external templates).
    """

    def is_accessible(self):
        self._current_user = current_user()
        return self._current_user is not None

    def _handle_view(self, *args, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('login', next=request.url))
        
        # Just call parent class with predefined model
        return super(AdminBaseView, self)._handle_view(*args, **kwargs)


class AdminModelView(ModelView):
    """
    View that will be used as model for some Admin views (without external templates).
    """

    def is_accessible(self):
        self._current_user = current_user()
        return self._current_user is not None

    def _handle_view(self, *args, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('login', next=request.url))
        
        # Just call parent class with predefined model
        return super(AdminModelView, self)._handle_view(*args, **kwargs)


##############################################################
#
# Main views
# 

class AdminView(MyAdminIndexView):
    """
    Admin View. Standard entry view which lets us see the index page.
    """
    
    @expose('/')
    def index(self):       
        return self.render('admin/index.html')


class UsersView(AdminModelView):
    """
    Users View. Entry view which lets us manage the users in the system.
    """
    
    column_list = ('login', 'name', 'email', 'organization', 'role')

    column_labels = dict(login = 'Login', name = 'Full Name', email = 'E-mail', organization = 'Organization', role = 'Role')
    column_filters = ('login', 'name', 'email', 'organization', 'role')

    column_descriptions = dict(login='Username (all letters, dots and numbers)',
                               name='First and Last name',
                               email='Valid e-mail address')

    # List of columns that can be sorted
    column_sortable_list = ('login', 'name', 'email', 'organization', 'role')
  
    # Columns that can used for searches
    column_searchable_list = ('login', 'name', 'email', 'organization', 'role')
 
    # Fields used for the creations of new users    
    form_columns = ('login', 'name', 'email', 'organization', 'role', 'password', 'creation_date', 'last_access_date')
    form_overrides = dict(access_level=wtf.SelectField, password=PasswordField)

    def __init__(self, session, **kwargs):
        super(UsersView, self).__init__(models.User, session, **kwargs)


class ApplicationsView(AdminBaseView):
    """
    Applications View. Entry view which lets us manage the applications in the system.
    """
    
    @expose('/')
    def index(self):       
        return self.render('admin/applications.html')


class ProfileView(AdminBaseView):
    """
    Profile View. Entry view which lets us edit our profile.
    """
    
    @expose('/')
    def index(self):       
        return self.render('admin/profile.html')



