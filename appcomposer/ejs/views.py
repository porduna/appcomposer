from flask import Blueprint

ejs_blueprint = Blueprint('ejs', __name__)

@ejs_blueprint.route("/")
def index():
    return ":-)"

