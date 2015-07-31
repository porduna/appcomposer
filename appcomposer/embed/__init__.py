from flask import Blueprint, render_template
from appcomposer import db
from appcomposer.babel import gettext
from appcomposer.models import EmbedApplication, EmbedApplicationTranslation

embed_blueprint = Blueprint('embed', __name__)

# 
# Public URLs
# 

@embed_blueprint.route('/apps/')
def apps():
    applications = db.session.query(EmbedApplication).order_by(EmbedApplication.last_update).all()
    return render_template("embed/apps.html", applications = applications, title = gettext("List of applications"))

@embed_blueprint.route('/apps/<identifier>/')
def app(identifier):
    application = db.session.query(EmbedApplication).filter_by(identifier = identifier).first()
    if application is None:
        return render_template("embed/error.html", message = gettext("Application '{identifier}' not found").format(identifier=identifier)), 404
    return render_template("embed/app.html", app = app, title = gettext("Application {name}").format(name=application.name))

@embed_blueprint.route('/apps/<identifier>/app.xml')
def app_xml(identifier):
    application = db.session.query(EmbedApplication).filter_by(identifier = identifier).first()
    if application is None:
        return render_template("embed/error.xml", message = gettext("Application '{identifier}' not found").format(identifier=identifier)), 404

    return

# 
# Management URLs
# 

@embed_blueprint.route('/')
def index():
    return ":-)"

