from flask import render_template
from appcomposer.composers.translate import translate_blueprint
from appcomposer.login import requires_login


@translate_blueprint.route("/about")
@requires_login
def translate_about():
    """
    Information about the translator application.
    """
    return render_template("composers/translate/about.html")

