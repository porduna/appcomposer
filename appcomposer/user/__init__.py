from flask import Blueprint, render_template

user_blueprint = Blueprint("user", __name__)

@user_blueprint.route("/")
def user_index():
    return render_template("user/index.html")

