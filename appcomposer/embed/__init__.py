import traceback
from flask import Blueprint, render_template, make_response, redirect

from appcomposer import db
from appcomposer.babel import gettext, lazy_gettext
from appcomposer.login import requires_golab_login, current_golab_user
from appcomposer.models import EmbedApplication, EmbedApplicationTranslation

from flask.ext.wtf import Form
from wtforms import TextField
from wtforms.validators import required
from wtforms.fields.html5 import URLField

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

    return render_template("embed/app.html", app = application, title = gettext("Application {name}").format(name=application.name))

@embed_blueprint.route('/apps/<identifier>/app.xml')
def app_xml(identifier):
    application = db.session.query(EmbedApplication).filter_by(identifier = identifier).first()
    if application is None:
        return render_template("embed/error.xml", message = gettext("Application '{identifier}' not found").format(identifier=identifier)), 404

    response = make_response(render_template("embed/app.xml", app = application, title = gettext("Application {name}").format(name=application.name)))
    response.content_type = 'application/xml'
    return response

# 
# Management URLs
# 

@embed_blueprint.route('/')
@requires_golab_login
def index():
    applications = db.session.query(EmbedApplication).filter_by(owner = current_golab_user()).order_by(EmbedApplication.last_update).all()
    return render_template("embed/index.html", applications = applications)

class ApplicationForm(Form):
    name = TextField(lazy_gettext("Name:"), validators=[required()])
    url = URLField(lazy_gettext("Web:"), validators=[required()])
    height = TextField(lazy_gettext("Height:"), validators=[required()])

@embed_blueprint.route('/create', methods = ['GET', 'POST'])
@requires_golab_login
def create():
    form = ApplicationForm()
    if form.validate_on_submit():
        application = EmbedApplication(url = form.url.data, name = form.name.data, owner = current_golab_user(), height=form.height.data)
        db.session.add(application)
        try:
            db.session.commit()
        except Exception as e:
            traceback.print_exc()
            return render_template("embed/error.html", message = gettext("There was an error creating an application")), 500
        else:
            return redirect(url_for('.edit', identifier=application.identifier))
            
    return render_template("embed/create.html", form=form, header_message=gettext("Add a web"))

@embed_blueprint.route('/edit/<identifier>/', methods = ['GET', 'POST'])
@requires_golab_login
def edit(identifier):
    application = db.session.query(EmbedApplication).filter_by(identifier = identifier).first()
    form = ApplicationForm(obj=application)
    if form.validate_on_submit():
        application.update(url=form.url.data, name=form.name.data, height=form.height.data)
        db.session.commit()
    return render_template("embed/create.html", form=form, header_message=gettext("Edit web"))

