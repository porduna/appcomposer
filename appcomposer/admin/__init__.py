from flask import Blueprint, render_template

# To be changed by Flask-Admin

admin_blueprint = Blueprint("admin", __name__)

@admin_blueprint.route("/")
def admin_index():
    return render_template("admin/index.html")

