from flask import Flask
import os

app = Flask(__name__)

# Configure flask app
app.config["DEBUG"] = True
app.config["SECRET_KEY"] = os.urandom(32)

#####
# Main components 
#####

from .user.user_application import UserApplication
from .admin import admin_blueprint


# User component
userApp = UserApplication(app)

app.register_blueprint(admin_blueprint,     url_prefix = '/admin')

#####
# Composers
#####

from .composers.translate import translate_blueprint
from .composers.adapt     import adapt_blueprint
from .composers.expert    import expert_blueprint

app.register_blueprint(translate_blueprint, url_prefix = '/composers/translate')
app.register_blueprint(adapt_blueprint,     url_prefix = '/composers/adapt')
app.register_blueprint(expert_blueprint,    url_prefix = '/composers/expert')

