
from flask import Flask
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose


class UserApplication(object):
    
    def __init__(self, flask_app):
        self.app = flask_app
        
        # Initialize the Admin
        # URL describes through which address we access the page.
        # Endpoint enables us to do url_for('userp') to yield the URL
        self.admin = Admin(self.app, index_view = HomeView(), name = "User Profile", url = "/user", endpoint = "user")
        
        #self.admin.add_view(EditView(name='Edit'))
        
        
class EditView(BaseView):
    @expose('/')
    def index(self):
        return self.render("index.html")
    
    
class HomeView(BaseView):
    
    def __init__(self):
        super(HomeView, self).__init__(endpoint = "user", url = "/user", static_folder="static", static_url_path="/static")
    
    @expose('/')
    def index(self):
        return self.render('user/index.html')
    
