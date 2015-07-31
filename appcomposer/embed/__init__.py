from flask import Blueprint, render_template
from appcomposer import db
from appcomposer.babel import gettext
from appcomposer.login import requires_golab_login, current_golab_user
from appcomposer.models import EmbedApplication, EmbedApplicationTranslation

from flask.ext.wtf import Form

embed_blueprint = Blueprint('embed', __name__)

@embed_blueprint.context_processor
def inject_variables():
    return dict(current_golab_user=current_golab_user)

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

    return render_template("embed/app.html", app = app, title = gettext("Application {name}").format(name=application.name))

# 
# Management URLs
# 

@embed_blueprint.route('/')
@requires_golab_login
def index():
    applications = db.session.query(EmbedApplication).filter_by(owner = current_golab_user()).order_by(EmbedApplication.last_update).all()
    return render_template("embed/index.html", applications = applications)

class ApplicationForm(Form):
    pass

@embed_blueprint.route('/create', methods = ['GET', 'POST'])
@requires_golab_login
def create():
    form = ApplicationForm()
    return render_template("embed/create.html", form=form)

@embed_blueprint.route('/edit/<identifier>/', methods = ['GET', 'POST'])
@requires_golab_login
def edit(identifier):
    form = ApplicationForm()
    return render_template("embed/edit.html", form=form)

