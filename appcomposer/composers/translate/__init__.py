from flask import Blueprint, render_template

translate_blueprint = Blueprint('translate', __name__)

@translate_blueprint.route("/")
def translate_index():
    return render_template("composers/translate/index.html")

