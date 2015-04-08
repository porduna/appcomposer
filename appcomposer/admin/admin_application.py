import datetime

from flask import redirect, request, url_for, Markup
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose
from flask.ext.admin.contrib.sqla import ModelView

from flask.ext import wtf
from wtforms.fields import PasswordField
from wtforms.validators import Email, Regexp, Optional

from appcomposer import models, db
from appcomposer.login import current_user, ROLES, Role, login_as, create_salted_password
from appcomposer.babel import lazy_gettext
from appcomposer.views import RedirectView


def _is_admin():
    _current_user = current_user()
    return _current_user and _current_user.role == Role.admin
        

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
    admin.add_view(AdminAppsView(name=lazy_gettext('Apps'), url = 'apps-admin', endpoint = 'admin.admin-apps'))      
    admin.add_view(RedirectView('user.profile.index', name=lazy_gettext('My Profile'), url = 'profile', endpoint = 'admin.profile'))
    admin.add_view(RedirectView('index', name=lazy_gettext('Back'), url = 'back', endpoint = 'admin.back'))

    category_translator = lazy_gettext("Translator")
    admin.add_view(KeySuggestionsView(name = lazy_gettext('Suggestions by key'), category = category_translator, endpoint = 'admin.suggestions-key'))
    admin.add_view(ValueSuggestionsView(name = lazy_gettext('Suggestions by value'), category = category_translator, endpoint = 'admin.suggestions-value'))
    admin.add_view(ActiveTranslationMessageView(name = lazy_gettext('Active translations'), category = category_translator, endpoint = 'admin.active-translations'))
    admin.init_app(app)

# Regular expression to validate the "login" field
LOGIN_REGEX = '^[A-Za-z0-9\._-][A-Za-z0-9\._-][A-Za-z0-9\._-][A-Za-z0-9\._-]*$'


#####################################################################
class MyAdminIndexView(AdminIndexView):
    """
    View that will be used as index for Admin.
    """

    def is_accessible(self):
        return _is_admin()

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
        return _is_admin()

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
        return _is_admin()

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

def login_as_formatter(v, c, req, p):
    return Markup("<a href='%(url)s' class='btn' >%(login)s</a>" % {
        'login' : req.login,
        'url' : url_for('.login_as', login = req.login),
    })


class UsersView(AdminModelView):
    """
    Users View. Entry view which lets us manage the users in the system.
    """
   
    column_list = ('login', 'name', 'email', 'organization', 'role', 'login_as')
    column_formatters = dict( login_as = login_as_formatter )
    # column_filters = ('login', 'name', 'email', 'organization', 'role')

    column_labels = dict(login = lazy_gettext('Login'), name = lazy_gettext('Full Name'), email = lazy_gettext('E-mail'), organization = lazy_gettext('Organization'), role = lazy_gettext('Role'), login_as = lazy_gettext('Login as'))

    column_descriptions = dict(login=lazy_gettext('Username (all letters, dots and numbers)'),
                               name=lazy_gettext('First and Last name'),
                               email=lazy_gettext('Valid e-mail address'),
                               login_as=lazy_gettext('Log in as you were that user'))

    # List of columns that can be sorted
    column_sortable_list = ('login', 'name', 'email', 'organization', 'role')
  
    # Columns that can used for searches
    column_searchable_list = ('login', 'name', 'email', 'organization', 'role')
 
    # Fields used for the creations of new users    
    form_columns = ('login', 'name', 'email', 'organization', 'role', 'auth_system', 'auth_data')
    
    sel_choices = []
    for role in ROLES:
        sel_choices.append( (role, lazy_gettext(role).title()) )

    auth_system_choices = []
    auth_system_choices.append(('graasp', 'graasp'))
    auth_system_choices.append(('userpass', 'Regular'))
    
    form_overrides = dict(auth_system = wtf.SelectField, auth_data=PasswordField, role=wtf.SelectField)        
    form_args = dict(email=dict(validators=[Email()]), login=dict(validators=[Regexp(LOGIN_REGEX)]), role=dict(choices = sel_choices), auth_system=dict(choices = auth_system_choices), auth_data = dict(validators=[Optional()]))
    
    def __init__(self, **kwargs):
        super(UsersView, self).__init__(models.User, db.session, **kwargs)

    @expose('/login_as/<login>/', methods = ['GET', 'POST'])
    def login_as(self, login):
        if not _is_admin():
            return "Something's going really wrong"

        if request.method == 'POST':
            login_as(login)
            return redirect(url_for('user.index'))

        return self.render("admin/login_as.html", login = login)

    def create_model(self, form):
        if form.auth_data.data == '':
            form.auth_data.errors.append(lazy_gettext("This field is required."))
            return False 

        form.auth_data.data = create_salted_password(form.auth_data.data)
        model = super(UsersView, self).create_model(form)
        model.creation_date = datetime.datetime.now()
        return model

    def update_model(self, form, model):
        old_auth_data = model.auth_data
        if form.auth_data.data != '':
            form.auth_data.data = create_salted_password(form.auth_data.data)
        return_value = super(UsersView, self).update_model(form, model)
        if form.auth_data.data == '':
            model.auth_data = old_auth_data
            self.session.add(model)
            self.session.commit()
        return return_value

class AdminAppsView(AdminModelView):
    """
    Admin Apps View. Basic entry view which lets us manage the applications located at the system.
    We will be able to filter, edit, and delete apps. The creation mode is disabled.
    """
    
    # The creation mode is disabled
    can_create = False

    column_list = ('owner', 'unique_id', 'name', 'composer')
    column_labels = dict(owner = lazy_gettext('Owner'), unique_id = lazy_gettext('ID'), name = lazy_gettext('Name'), composer = lazy_gettext('Composer'))
    column_sortable_list = ('unique_id', 'name', 'composer')
    column_searchable_list = ('unique_id', 'name', 'composer')
    # column_filters = ('unique_id', 'name', 'composer', 'creation_date', 'modification_date', 'last_access_date')
   
    # Information needed when creating a new composer (not used at the moment)
    form_columns = ('owner', 'name', 'composer') 
    sel_choices = [(level, level.title()) for level in (lazy_gettext('translate'), lazy_gettext('adapt'),lazy_gettext('dummy'))] # TODO: find where this is registered in case of activate the creation mode
    form_overrides = dict(composer=wtf.SelectField)
    form_args = dict(composer=dict(choices=sel_choices))   
   
    def __init__(self, **kwargs):
        super(AdminAppsView, self).__init__(models.App, db.session, **kwargs)

    # This function is used when deleting an app in the system    
    def on_model_delete(self, model):                
        # Delete every AppVar for that App
        #print "App Id: " + model.unique_id
        app = models.App.query.filter_by(unique_id=model.unique_id).first()        
        models.AppVar.query.filter_by(app=app).delete()
    
class KeySuggestionsView(AdminModelView):
    column_searchable_list = ('key', 'language', 'target', 'value')
    column_sortable_list = ('key', 'language', 'target')

    def __init__(self, **kwargs):
        super(KeySuggestionsView, self).__init__(models.TranslationKeySuggestion, db.session, **kwargs)

class ValueSuggestionsView(AdminModelView):
    column_searchable_list = ('human_key', 'language', 'target', 'value')
    column_sortable_list = ('human_key', 'language', 'target')

    def __init__(self, **kwargs):
        super(ValueSuggestionsView, self).__init__(models.TranslationValueSuggestion, db.session, **kwargs)

class ActiveTranslationMessageView(AdminModelView):
    column_list = ('bundle.translation_url.url', 'bundle.language', 'bundle.target', 'key', 'value', 'history.datetime', 'history.user')
    column_searchable_list = ('key','value')

    def __init__(self, **kwargs):
        super(ActiveTranslationMessageView, self).__init__(models.ActiveTranslationMessage, db.session, **kwargs)
