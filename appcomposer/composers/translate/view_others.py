from flask import render_template
from appcomposer.composers.translate import translate_blueprint


@translate_blueprint.route("/about")
def translate_about():
    """Information about the translator application."""
    return render_template("composers/translate/about.html")