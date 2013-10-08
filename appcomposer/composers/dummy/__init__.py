from flask import Blueprint, render_template

dummy_blueprint = Blueprint('dummy', __name__)

@dummy_blueprint.route("/")
def dummy_index():
    return render_template("composers/dummy/index.html")
