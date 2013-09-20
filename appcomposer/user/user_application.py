
from flask import Flask
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose
from flask.ext.wtf import TextField, Form, PasswordField, NumberRange
from .fields import DisabledTextField


class UserApplication(object):
    
    def __init__(self, flask_app):
        self.app = flask_app
        
        # Initialize the Admin
        # URL describes through which address we access the page.
        # Endpoint enables us to do url_for('userp') to yield the URL
        self.admin = Admin(self.app, index_view = HomeView(), name = "User Profile", url = "/user", endpoint = "user")
        
        self.admin.add_view(EditView(name='Edit'))
        self.admin.add_view(ProfileEditView(None, name="Profile"))
        
        
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
    full_name   = DisabledTextField(u"Full name:")
    login       = DisabledTextField(u"Login:")
    email       = TextField(u"E-mail:")
    facebook    = TextField(u"Facebook id:", description="Facebook identifier (number).", validators = [NumberRange(min=1000) ])
    password    = PasswordField(u"Password:", description="Password.")

class ProfileEditView(BaseView):

    def __init__(self, db_session, *args, **kwargs):
        super(ProfileEditView, self).__init__(*args, **kwargs)

        self._session = db_session

    @expose(methods=['GET','POST'])
    def index(self):
#         login = get_app_instance().get_user_information().login
#         user = self._session.query(model.DbUser).filter_by(login = login).one()
#         
#         facebook_id = ''
# 
#         user_auths = {}
#         change_password = True
#         password_auth = None
#         facebook_auth = None
# 
#         for user_auth in user.auths:
#             if user_auth.auth.auth_type.name.lower() == 'facebook':
#                 facebook_id = user_auth.configuration
#                 facebook_auth = user_auth
#             if 'ldap' in user_auth.auth.auth_type.name.lower():
#                 change_password = False
#             if user_auth.auth.auth_type.name.lower() == 'db':
#                 password_auth = user_auth
# 
# 

        # TODO: Probably we shouldn't disable CSRF. At least, in the Weblab code which I'm using as example
        # that is not done. Check how to handle the secret_key, and what it implies.
        form = ProfileEditForm(csrf_enabled = False)
        form.full_name.data = "Luis"
        form.login.data = "lrg"
        form.email.data = "mail@dotcom"
        form.facebook.data = "facebook"
             
#          if len(request.form):
#              form = ProfileEditForm(request.form)
#          else:
#              form = ProfileEditForm()
#              form.full_name.data = user.full_name
#              form.login.data     = user.login
#              form.email.data     = user.email
#              form.facebook.data  = facebook_id
 
#         user_permissions = get_app_instance().get_permissions()
#         
#         change_profile = True
#         for permission in user_permissions:
#             if permission.name == permissions.CANT_CHANGE_PROFILE:
#                 change_password = False
#                 change_profile  = False
# 
#         if change_profile and form.validate_on_submit():
# 
#             errors = []
# 
#             if change_password and password_auth is not None and form.password.data:
#                 if len(form.password.data) < 6:
#                     errors.append("Error: too short password")
#                 else:
#                     password_auth.configuration = self._password2sha(form.password.data)
# 
#             user.email = form.email.data
#             
#             if form.facebook.data:
#                 if facebook_auth is None:
#                     auth = self._session.query(model.DbAuth).filter_by(name = 'FACEBOOK').one()
#                     new_auth = model.DbUserAuth(user, auth, form.facebook.data)
#                     self._session.add(new_auth)
#                 else:
#                     facebook_auth.configuration = form.facebook.data
#             else:
#                 if facebook_auth is not None:
#                     self._session.delete(facebook_auth)
# 
#             self._session.commit()
# 
#             if errors:
#                 for error in errors:
#                     flash(error)
#             else:
#                 flash("Saved")

        return self.render("user/profile-edit.html", form=form)
#        return self.render("profile-edit.html", form=form, change_password=change_password, change_profile=change_profile)
    
