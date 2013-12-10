from flask import Blueprint, flash, json, redirect, render_template, request, session, url_for

import appcomposer.appstorage.api as appstorage
#from appcomposer.appstorage.api import create_app, get_app, update_app_data

from forms import AdaptappCreateForm

# Required imports for a customized app view for the adapt tool (a possible block to be refactored?)
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose
from appcomposer.application import COMPOSERS, COMPOSERS_DICT
from appcomposer.models import App
from appcomposer.db import db_session

info = {
    'blueprint': 'adapt',
    'url': '/composers/adapt',

    'index_endpoint': 'adapt.adapt_index',
    'create_endpoint': 'adapt.adapt_create',    
    'edit_endpoint': 'adapt.adapt_edit',
    'open_endpoint': 'adapt.adapt_open',    

    'name': 'Adaptor Composer',
    'description': 'Adapt an existing app.'
}

adapt_blueprint = Blueprint(info['blueprint'], __name__)


@adapt_blueprint.route("/")
def adapt_index():    
    #ONLY for testing purposes: the session must be retrieved from the main page 
    if not session.get("logged_in", False):
        session["logged_in"] = True
        session["login"] = "testuser"
        return redirect(url_for('adapt.adapt_index'))
    return render_template("composers/adapt/index.html")        


@adapt_blueprint.route("/create", methods=["GET", "POST"])
def adapt_create():

    # If we receive a get we just show the new app form and the list of adapt apps    
    if request.method == "GET":               
        apps = db_session.query(App).filter_by(owner_id=1).all()

        def build_edit_link(app):
            endpoint = COMPOSERS_DICT[app.composer]["edit_endpoint"]
            return url_for(endpoint, appid=app.unique_id)

        return render_template('composers/adapt/create.html', apps=apps, build_edit_link=build_edit_link) 

    # If we receive a post we are creating an experiment .
    elif request.method == "POST":
        name = request.form["appname"]

        try:
            app = appstorage.create_app(name, "dummy", data='{"text":""}')
        except appstorage.AppExistsException:
            flash("An App with that name already exists", "error")
            return render_template("composers/adapt/create.html", name=name)

        return redirect(url_for("adapt.adapt_edit", appid=app.unique_id))        

@adapt_blueprint.route("/export/<app_id>/edt/edt.html")
def edt_index(app_id):
    # In the templates, edt.html points to {{ url_for('adapt.edt_domain', app_id = app_id) }} 
    # instead of buoyancy.js
    # The domain name is also generated here.
    domain_name = 'buoyancy'
    experiment_name = 'Archimedes'
    return render_template("composers/adapt/edt/edt.html", app_id = app_id, domain_name = domain_name, experiment_name = experiment_name)


@adapt_blueprint.route("/export/<app_id>/edt/domain.js")
def edt_domain(app_id):
    domain = {
        # This variable stores all the information required for the domain
        'name': 'buoyancy',
        'description': 'Buoyancy is an upward force exerted by a fluid.',
        'object_properties': [
            {'name': 'mass', 'type': 'magnitude', 'symbol': 'm', 'unit': 'kg'},
            {'name': 'volume', 'type': 'magnitude', 'symbol': 'V', 'unit': 'm^3'},
            {'name': 'density', 'type': 'magnitude', 'symbol': 'rho', 'unit': 'kg / m^3'},
            {'name': 'material', 'type': 'multitude', 'values': '*'},
            {'name': 'shape', 'type': 'multitude', 'values': '*'}
        ],
        'object_relations': [
            {'name': 'density', 'object_properties': [ 'density', 'mass', 'volume' ], 'relation': 'density = mass / volume'}
        ],
        'system_properties': [
            {'name': 'fluid_aquarium', 'type': 'multitude', 'values': '*'},
            {'name': 'fluid_density', 'type': 'multitude', 'symbol': 'rho', 'unit': 'kg / m^3'},
            {'name': 'fluid_column', 'type': 'multitude', 'symbol': 'h', 'unit': 'm'}
        ],
        'object_measures': [
            {'name': 'water_displacement', 'type': 'magnitude', 'unit': 'm^3', 'depends_on': { 'object_properties': ['mass'], 'system_properties': ['fluid_density']}},
            {'name': 'sink_or_float', 'type': 'multitude', 'values': ['sinks', 'floats'], 'depends_on': { 'object_properties': ['density'], 'system_properties': ['fluid_density']}}
        ] 
    }

    experiment = {
        # This variable stores all the information required for the experiment
        'name': 'Archimedes',
	    'description': 'Simulation-based version of the buoyancy experiment',
	    'domain': 'buoyancy',
	    'object_property_selection': ['mass', 'volume', 'shape'],
	    'object_measure_selection': ['sink_or_float', 'water_displacement'],
	    'system_property_selection': ['fluid_aquarium'],
	    'object_property_specification': [
            {'property': 'mass', 'initial': '300', 'unit': 'gram', 'range': {'minimum': '50', 'maximum': '500', 'increment': '50'}},
            {'property': 'volume','initial': '200', 'unit': 'cm_3', 'range': {'minimum': '50', 'maximum': '500', 'increment': '50'}},
            {'property': 'shape', 'initial': 'sphere', 'values': ['sphere', 'cube']}
        ],
	    'system_property_values': [
            {'property': 'fluid_aquarium', 'value': 'water'},
	        {'property': 'density', 'value': '1.0'}
        ]
    }
    
    return render_template("composers/adapt/edt/domain.js", domain = json.dumps(domain, indent = 4), experiment = json.dumps(experiment, indent = 4))


@adapt_blueprint.route("/edit", methods = ['GET', 'POST'])
def adapt_edit():
    # Author an adapt app with appid = appid    
    # If we receive a get we just want to show the page.
    if request.method == "GET":
        appid = request.args.get("appid")
        if not appid:
            return "appid not provided", 400
        app = appstorage.get_app(appid)
        if app is None:
            return "App not found", 500

        data = json.loads(app.data)
        text = data["text"]

        return render_template("composers/adapt/edit.html", app=app, text=text)
    elif request.method == "POST":
        appid = request.form["appid"]
        text = request.form["domain_name"]

        # Retrieve the app we're editing by its id.
        app = appstorage.get_app(appid)

        # Build our dummy composer JSON.
        data = {
            "dummy_version": 1,
            "text": text}

        appstorage.update_app_data(app, data)

        flash("Saved successfully", "success")

        # TODO: Print a success message etc etc.

        # If the user clicks on "Save & exit", then we redirect him to the app page,
        # otherwise we stay here.
        '''
        if "saveexit" in request.form:
            return redirect(url_for("user.apps.index"))
        '''
        return render_template("composers/adapt/edit.html", app=app, text=text)


@adapt_blueprint.route("/open", methods=["GET", "POST"])
def adapt_open():
    # Edit an existing adapt app with appid = appid
    # TODO: This method is a variant of "new" with the appid
    if request.method == "GET":
        appid = request.args.get("appid")
        if not appid:
            return "appid not provided", 400
        app = appstorage.get_app(appid)
        if app is None:
            return "App not found", 500

        data = json.loads(app.data)
        text = data["text"]

        return render_template("composers/adapt/edit.html", app=app, text=text)
    elif request.method == "POST":
        appid = request.form["appid"]
        text = request.form["domain_name"]

        # Retrieve the app we're editing by its id.
        app = appstorage.get_app(appid)

        # Build our dummy composer JSON.
        data = {
            "dummy_version": 1,
            "text": text}

        appstorage.update_app_data(app, data)

        flash("Saved successfully", "success")

        # TODO: Print a success message etc etc.

        # If the user clicked on saveexit we redirect to appview, otherwise
        # we stay here.
        if "saveexit" in request.form:
            return redirect(url_for("user.apps.index"))

        return render_template("composers/dummy/edit.html", app=app, text=text)
