from flask import Blueprint, render_template

appstorage_blueprint = Blueprint("appstorage", __name__)

@appstorage_blueprint.route("/")
def user_index():
    return render_template("appstorage/index.html")