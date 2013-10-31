from flask import redirect, request, flash, session, render_template_string, url_for
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose

from appcomposer.login import current_user


def initialize_admin_component(app):
    # Initialize the Admin
    # URL describes through which address we access the page.
    # Endpoint enables us to do url_for('userp') to yield the URL
    url = '/admin'
    admin = Admin(index_view = AdminView(url = url, endpoint = 'admin'), name='Admin Profile', endpoint = "home-admin")
    admin.add_view(UsersView(name='Users', url = 'users', endpoint = 'admin.users'))
    admin.add_view(ApplicationsView(name='Applications', url = 'applications', endpoint = 'admin.applications'))    
    admin.add_view(ProfileView(name='My Profile', url = 'profile', endpoint = 'admin.profile'))    
    admin.init_app(app)



class AdminBaseView(BaseView):

    def is_accessible(self):
        return current_user() is not None

    def _handle_view(self, *args, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('login', next=request.url))

        return super(AdminBaseView, self)._handle_view(*args, **kwargs)


class AdminView(AdminBaseView):
    
    @expose('/')
    def index(self):       
        return self.render('admin/index.html')


class UsersView(AdminBaseView):
    
    @expose('/')
    def index(self):       
        return self.render('admin/users.html')


class ApplicationsView(AdminBaseView):
    
    @expose('/')
    def index(self):       
        return self.render('admin/applications.html')


class ProfileView(AdminBaseView):
    
    @expose('/')
    def index(self):       
        return self.render('admin/profile.html')



