from flask import Blueprint, render_template

adapt_blueprint = Blueprint('adapt', __name__)

@adapt_blueprint.route("/")
def adapt_index():
    return render_template("adapt/index.html")

