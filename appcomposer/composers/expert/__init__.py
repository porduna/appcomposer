from flask import Blueprint, render_template

from appcomposer.models import App

expert_blueprint = Blueprint('expert', __name__)

@expert_blueprint.route("/")
def expert_index():
    return render_template("composers/expert/index.html")

