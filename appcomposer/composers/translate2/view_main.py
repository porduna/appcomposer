from flask import render_template
from appcomposer.composers.translate2 import translate2_blueprint


@translate2_blueprint.route("/")
def index():
    return render_template("composers/translate2/index.html")