from flask import Flask

app = Flask(__name__)

from .translate import translate_blueprint
from .adapt     import adapt_blueprint
from .expert    import expert_blueprint

app.register_blueprint(translate_blueprint, url_prefix = '/apps/translate')
app.register_blueprint(adapt_blueprint,     url_prefix = '/apps/adapt')
app.register_blueprint(expert_blueprint,    url_prefix = '/apps/expert')

