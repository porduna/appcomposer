from flask import Flask, url_for, render_template, escape

app = Flask(__name__)

# Main components 

from .user  import user_blueprint
from .admin import admin_blueprint
from .appstorage import appstorage_blueprint

app.register_blueprint(user_blueprint, url_prefix = '/user')
app.register_blueprint(admin_blueprint, url_prefix = '/admin')
app.register_blueprint(appstorage_blueprint, url_prefix = '/appstorage')


# Composers

from .composers.translate import translate_blueprint
from .composers.adapt     import adapt_blueprint
from .composers.expert    import expert_blueprint

app.register_blueprint(translate_blueprint, url_prefix = '/composers/translate')
app.register_blueprint(adapt_blueprint,     url_prefix = '/composers/adapt')
app.register_blueprint(expert_blueprint,    url_prefix = '/composers/expert')



