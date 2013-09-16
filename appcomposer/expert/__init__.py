from flask import Blueprint, render_template

expert_blueprint = Blueprint('expert', __name__)

@expert_blueprint.route("/")
def expert_index():
    return render_template("expert/index.html")

