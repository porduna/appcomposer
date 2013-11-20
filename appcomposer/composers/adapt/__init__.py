from flask import Blueprint, render_template
import appcomposer.appstorage.api as appstorage

adapt_blueprint = Blueprint('adapt', __name__)

@adapt_blueprint.route("/")
def adapt_index():
    return render_template("composers/adapt/index.html")

@adapt_blueprint.route("/export/<app_id>/edt/edt.html")
def edt_index(app_id):
    # In the templates, edt.html points to {{ url_for('adapt.edt_domain', app_id = app_id) }} 
    # instead of buoyancy.js
    return render_template("composers/adapt/edt/edt.html", app_id = app_id)

@adapt_blueprint.route("/export/<app_id>/edt/domain.js")
def edt_domain(app_id):
    # In the beginning, this is simply the buoyancy.js.
    return render_template("composers/adapt/edt/domain.js")
