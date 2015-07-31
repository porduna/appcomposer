from flask import Blueprint

embed_blueprint = Blueprint('embed', __name__)

@embed_blueprint.route('/')
def index():
    return ":-)"
