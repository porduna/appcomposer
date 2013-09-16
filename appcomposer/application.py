from flask import Flask

app = Flask(__name__)

from .composers.translate import translate_blueprint
from .composers.adapt     import adapt_blueprint
from .composers.expert    import expert_blueprint

app.register_blueprint(translate_blueprint, url_prefix = '/composers/translate')
app.register_blueprint(adapt_blueprint,     url_prefix = '/composers/adapt')
app.register_blueprint(expert_blueprint,    url_prefix = '/composers/expert')

