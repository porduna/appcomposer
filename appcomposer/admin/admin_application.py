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
    admin = Admin(index_view = AdminView(url = url, endpoint = 'admin'), name='Admin Profile', endpoint = "home-admin")
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

    def is_accessible(self):
        self._current_user = current_user()
        return self._current_user is not None

    def _handle_view(self, *args, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('login', next=request.url))
        
        # Just call parent class with predefined model
        return super(MyAdminIndexView, self)._handle_view(*args, **kwargs)


class AdminBaseView(BaseView):

    def is_accessible(self):
        self._current_user = current_user()
        return self._current_user is not None

    def _handle_view(self, *args, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('login', next=request.url))
        
        # Just call parent class with predefined model
        return super(AdminBaseView, self)._handle_view(*args, **kwargs)


class AdminModelView(ModelView):

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
    
    @expose('/')
    def index(self):       
        return self.render('admin/index.html')


class UsersView(AdminModelView):
    
    column_list = ('login', 'name', 'email', 'organization', 'role')

    def __init__(self, session, **kwargs):
        super(UsersView, self).__init__(models.User, session, **kwargs)

    column_labels = dict(login = 'Login', name = 'Full Name', email = 'E-mail', organization = 'Organization', role = 'Role')
    column_filters = ('login', 'name', 'email', 'organization', 'role')

    # List of columns that can be sorted
    column_sortable_list = ('login', 'name', 'email', 'organization', 'role')
  
    # Columns that can used for searches
    column_searchable_list = ('login', 'name', 'email', 'organization', 'role')
       
    # Fields used for the creations of new users    
    #form_columns = ('login', 'name', 'email', 'organization', 'role')
    #form_overrides = dict(access_level=wtf.SelectField, password=PasswordField)

    #def on_model_change(self, form, model):
    #    model.password = new_hash("sha", model.password).hexdigest()

class ApplicationsView(AdminBaseView):
    
    @expose('/')
    def index(self):       
        return self.render('admin/applications.html')


class ProfileView(AdminBaseView):
    
    @expose('/')
    def index(self):       
        return self.render('admin/profile.html')



