from flask import Flask, request
from flask import escape
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(32)
app.config['SESSION_COOKIE_NAME'] = 'appcompsession'
app.config['SQLALCHEMY_NATIVE_UNICODE'] = True
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600
app.config.from_object('config')

# Support old deployments
if not app.config.get('SQLALCHEMY_DATABASE_URI', False):
    if app.config.get('SQLALCHEMY_ENGINE_STR', False):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_ENGINE_STR']


from appcomposer.babel import Babel

if Babel is None:
    print "Not using Babel. Everything will be in English"
else:
    babel = Babel(app)

    supported_languages = ['en']
    supported_languages.extend([ translation.language for translation in babel.list_translations() ])

    @babel.localeselector
    def get_locale():
        locale = request.args.get('locale',  None)
        if locale is None:
            locale = request.accept_languages.best_match(supported_languages)
        if locale is None:
            locale = 'en'
        return locale

###
# Composers info
###

from .composers.dummy import info as dummy_info
from .composers.translate import info as translate_info
from .composers.adapt import info as adapt_info

# So that we can have access to all the info from the Users component.
# It is important that this is done early. Otherwise, it will be accessed by the
# user component before it is ready.
COMPOSERS = [translate_info, adapt_info]
COMPOSERS_DICT = {info["blueprint"]: info for info in COMPOSERS}
COMPOSERS_DICT[dummy_info['blueprint']] = dummy_info

def register_dummy():
    COMPOSERS.insert(0, dummy_info)

app.config['COMPOSERS'] = COMPOSERS

# TODO: The COMPOSERS_DICT thing is not very pretty. Find a work-around.


#####
# Main components 
#####

#
# Initialize administration panels
# 

# User component
from .user.user_application import initialize_user_component
initialize_user_component(app)


# Admin component
from .admin.admin_application import initialize_admin_component
initialize_admin_component(app)


#####
# Composers
#####

from .composers.translate import translate_blueprint
from .composers.adapt import adapt_blueprint
from .composers.expert import expert_blueprint
from .composers.dummy import dummy_blueprint


app.register_blueprint(translate_blueprint, url_prefix='/composers/translate')
app.register_blueprint(adapt_blueprint, url_prefix='/composers/adapt')
app.register_blueprint(expert_blueprint, url_prefix='/composers/expert')
app.register_blueprint(dummy_blueprint, url_prefix=dummy_info["url"])



# Mostly for debugging purposes, this snippet will print the site-map so that we can check
# which methods we are routing.
@app.route("/site-map")
def site_map():
    lines = []
    for rule in app.url_map.iter_rules():
        line = str(escape(repr(rule)))
        lines.append(line)

    ret = "<br>".join(lines)
    return ret
