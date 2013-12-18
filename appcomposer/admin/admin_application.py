import datetime

from flask import redirect, request, flash, session, render_template_string, url_for
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose
from flask.ext.admin.contrib.sqla import ModelView

from flask.ext import wtf
from wtforms.fields import PasswordField
from wtforms.validators import Email, Regexp

from appcomposer import models, db
from appcomposer.login import current_user
from appcomposer.babel import lazy_gettext

# List of all available composers
from appcomposer.application import COMPOSERS, COMPOSERS_DICT

##########################################################
#
# Initialization
# 

def initialize_admin_component(app):
    # Initialize the Admin
    # URL describes through which address we access the page.
    # Endpoint enables us to do url_for('userp') to yield the URL
    url = '/admin'
    admin = Admin(index_view = AdminView(url = url, endpoint = 'admin'), name=lazy_gettext('Admin Profile'), endpoint = "home-admin")
    admin.add_view(UsersView(name=lazy_gettext('Users'), url = 'users', endpoint = 'admin.users'))
    #admin.add_view(BasicAdminAppsView(name=lazy_gettext('Basic App View'), url = 'basic-apps-admin', endpoint = 'admin.basic-admin-apps'))    
    admin.add_view(AdvancedAdminAppsView(name=lazy_gettext('Apps View'), url = 'advanced-apps-admin', endpoint = 'admin.advanced-admin-apps'))   
    admin.add_view(ProfileView(name=lazy_gettext('My Profile'), url = 'profile', endpoint = 'admin.profile'))
    admin.add_view(BackView(name=lazy_gettext('Back'), url = 'back', endpoint = 'admin.back'))     
    admin.init_app(app)

# Regular expression to validate the "login" field
LOGIN_REGEX = '^[A-Za-z0-9\._-][A-Za-z0-9\._-][A-Za-z0-9\._-][A-Za-z0-9\._-]*$'


#####################################################################
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

    column_labels = dict(login = lazy_gettext('Login'), name = lazy_gettext('Full Name'), email = lazy_gettext('E-mail'), organization = lazy_gettext('Organization'), role = lazy_gettext('Role'))
    column_filters = ('login', 'name', 'email', 'organization', 'role')

    column_descriptions = dict(login=lazy_gettext('Username (all letters, dots and numbers)'),
                               name=lazy_gettext('First and Last name'),
                               email=lazy_gettext('Valid e-mail address'))

    # List of columns that can be sorted
    column_sortable_list = ('login', 'name', 'email', 'organization', 'role')
  
    # Columns that can used for searches
    column_searchable_list = ('login', 'name', 'email', 'organization', 'role')
 
    # Fields used for the creations of new users    
    form_columns = ('login', 'name', 'email', 'organization', 'role', 'password')
    sel_choices = [(level, level.title()) for level in (lazy_gettext('administrator'), lazy_gettext('teacher'))] # TODO: establish different permisions in the system   
    
    form_overrides = dict(access_level=wtf.SelectField, password=PasswordField, role=wtf.SelectField)        
    form_args = dict(email=dict(validators=[Email()]), login=dict(validators=[Regexp(LOGIN_REGEX)]), role=dict(choices=sel_choices))
    
    def __init__(self, **kwargs):
        super(UsersView, self).__init__(models.User, db.session, **kwargs)

    # This function is used when creating a new empty composer    
    def on_model_change(self, form, model):                
        model.auth_system = 'userpass'
        model.auth_data = model.password
        model.creation_date = datetime.datetime.now()
        model.last_access_date = datetime.datetime.now()
        

class BasicAdminAppsView(AdminModelView):
    """
    Basic Admin Apps View. Basic entry view which lets us manage the applications located at the system.
    We will be able to create, edit, and delete apps.
    """

    column_list = ('owner_id', 'unique_id', 'name', 'composer', 'creation_date', 'modification_date', 'last_access_date')
    column_labels = dict(owner_id = lazy_gettext('Owner'), unique_id = lazy_gettext('ID'), name = lazy_gettext('Name'), composer = lazy_gettext('Composer'), creation_date = lazy_gettext('Creation Date'), modification_date = lazy_gettext('Modification Date'), last_access_date = lazy_gettext('Last Access Date'))
    column_sortable_list = ('unique_id', 'name', 'composer')
    column_searchable_list = ('unique_id', 'name', 'composer')
   
    # Information needed when creating a new composer
    form_columns = ('owner_id', 'name', 'composer') 
    sel_choices = [(level, level.title()) for level in (lazy_gettext('translate'), lazy_gettext('adapt'),lazy_gettext('dummy'))] # TODO: find where this is registered
    form_overrides = dict(composer=wtf.SelectField)
    form_args = dict(composer=dict(choices=sel_choices))   
   
    def __init__(self, **kwargs):
        super(BasicAdminAppsView, self).__init__(models.App, db.session, **kwargs)


class AdvancedAdminAppsView(AdminBaseView):
    """
    Advanced Admin Apps View. Advanced entry view which lets us manage the applications located at the system. 
    We will be able to create, edit, and delete apps.
    """

    @expose('/')
    def index(self):
        # Retrieve the apps
        apps = db.session.query(models.App).all()
        
        def build_edit_link(app):
            endpoint = COMPOSERS_DICT[app.composer]["edit_endpoint"]
            return url_for(endpoint, appid=app.unique_id)

        def build_delete_link(app):
            endpoint = COMPOSERS_DICT[app.composer]["delete_endpoint"]
            return url_for(endpoint, appid=app.unique_id)

        return self.render('admin/advanced-admin-apps.html', composers=COMPOSERS, apps=apps, build_edit_link=build_edit_link,
                           build_delete_link=build_delete_link)


class ProfileView(AdminBaseView):
    """
    Profile View. Entry view which lets us edit our profile.
    """
    
    @expose('/')
    def index(self):       
        return self.render('admin/profile.html')


class BackView(AdminBaseView):
    """
    Back View.Entry view which lets us come back to the initial page.
    """
    
    @expose('/')
    def index(self):       
        return self.render('index.html')
