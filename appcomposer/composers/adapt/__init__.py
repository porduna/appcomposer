from flask import Blueprint, flash, json, redirect, render_template, request, session, url_for

import appcomposer.appstorage.api as appstorage
from appcomposer.appstorage.api import create_app, get_app, update_app_data, db_session

from forms import AdaptappCreateForm

# Required imports for a customized app view for the adapt tool (a possible block to be refactored?)
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose
from appcomposer.application import COMPOSERS, COMPOSERS_DICT
from appcomposer.models import App


info = {
    'blueprint': 'adapt',
    'url': '/composers/adapt',

    'new_endpoint': 'adapt.adapt_index',
    'create_endpoint': 'adapt.adapt_create',    
    'edit_endpoint': 'adapt.adapt_edit',
    'open_endpoint': 'adapt.adapt_open', 
    'delete_endpoint': 'dummy.delete',         

    'name': 'Adaptor Composer',
    'description': 'Adapt an existing app.'
}

adapt_blueprint = Blueprint(info['blueprint'], __name__)


@adapt_blueprint.route("/", methods=["GET", "POST"])
def adapt_index():
    """
    adapt_index()
    Loads the main page with the selection of adaptor apps (concept map, hypothesis or experiment design).
    @return: The adaptor type that the user has selected.
    """        
 
    if request.method == "GET":    

        #We log in automatically as "testuser". ONLY for testing purposes: the session must be retrieved from the main page        
        if not session.get("logged_in", False):
            session["logged_in"] = True
            session["login"] = "testuser"
            return redirect(url_for('adapt.adapt_index'))
        return render_template("composers/adapt/index.html")       
         
    elif request.method == "POST":

        adaptor_type = request.form["adaptor_type"]
        if adaptor_type is None:
            flash("adaptor_type not present", "error")

            # An adaptor_type is required.
            return redirect(url_for("adapt.adapt_index"))    
                                        
        return redirect(url_for("adapt.adapt_create", adaptor_type = adaptor_type))


@adapt_blueprint.route("/create", methods=["GET", "POST"])
def adapt_create():
    """
    adapt_create()
    Loads the form for creating new adaptor apps and the list of adaptor apps from a specific type.
    @return: The app unique id and its name.
    """    
    
    apps = db_session.query(App).filter_by(owner_id=1).all()    
    adaptor_type = request.args.get("adaptor_type")  

    def build_edit_link(app):
        return url_for("adapt.adapt_edit", app_id=app.unique_id, adaptor_type = adaptor_type)  

    # If a get request is received, we just show the new app form and the list of adaptor apps    
    if request.method == "GET":               
                   
        if not adaptor_type:
            flash("adaptor_type not received", "error")            
            return "Missing parameters (Adaptor Type)", 400                     

        return render_template('composers/adapt/create.html', apps=apps, adaptor_type = adaptor_type, build_edit_link=build_edit_link) 

    # If a post is received, we are creating an adaptor app.
    elif request.method == "POST":
                   
        name = request.form["app_name"]
        description = request.form["app_description"]      
        adaptor_type = request.form["adaptor_type"]                      

        # Build the adaptor composer JSON schema.
             
        data = {
            "dummy_version": 1,
            "name": name,
            "description": description,
            "adaptor_type": adaptor_type,
            "concepts": [],
            "conditionals": "", 
            "inputs": "",
            "outputs": ""}

        try:
            app = appstorage.create_app(name, "dummy", data)
        except appstorage.AppExistsException:
            flash("An App with that name already exists", "error")
                        
            return render_template("composers/adapt/create.html", name=name, apps = apps, adaptor_type = adaptor_type, build_edit_link=build_edit_link)

        return redirect(url_for("adapt.adapt_edit", app_id =app.unique_id, app_name = name, adaptor_type = adaptor_type))        


@adapt_blueprint.route("/edit", methods = ['GET', 'POST'])
def adapt_edit():
    """
    adapt_edit()
    Form-based user interface for editing the contents of an adaptor app.
    @return: The final app with all its fields stored in the database.
    """        
         
    # If we receive a get we just want to show the page.
    if request.method == "GET":
        
        app_id = request.args.get("app_id")
        adaptor_type = request.args.get("adaptor_type")
                
        if not app_id:
            return "app_id not provided", 400
        app = appstorage.get_app(app_id)
        if app is None:
            return "App not found", 500
        
        data = json.loads(app.data)
        concepts = data["concepts"]                                

        return render_template("composers/adapt/edit.html", app=app, concepts = concepts, adaptor_type = adaptor_type)
    
    elif request.method == "POST":
        
        app_id = request.form["app_id"]                 
        
        # Retrieve the list of concepts                
        concepts = json.dumps(request.form["concepts"] .split(','))
        
        # Select the app we're editing by its id.
        app = appstorage.get_app(app_id)
        
        data = json.loads(app.data)     
        name = request.args.get("app_name")  
        
        # FIX: App data is not saved,
        #description = app.data["description"]     
        #adaptor_type = app.data["adaptor_type"]    

        # Build the adaptor composer JSON.
        data = {
            "dummy_version": 1,
            "name": name,
            "description": "",
            "adaptor_type": "",
            "concepts": concepts,
            "conditionals": "", 
            "inputs": "",
            "outputs": ""}    

        #flash(data, "success") 
        #flash(app.data, "success")  
        #-- DIFFERENCE between these two variables? First: single quotes. Second: double quotes

        appstorage.update_app_data(app, data)
        #flash(concepts, "success")
        flash("Saved successfully", "success")        

        return render_template("composers/adapt/edit.html", app=app, concepts = data["concepts"])


@adapt_blueprint.route("/export/<app_id>/conceptmapper/conceptmapper.html")
def conceptmapper_index(app_id):
    """
    conceptmapper_index(app_id)
    This function points to the concept map instance.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.    
    @return: The webpage of a concept map.
    """  
        
    # In the templates, conceptmapper.html points to {{ url_for('adapt.conceptmapper_domain', app_id = app_id) }} 
    # instead of domain.js (In the original app, the "concepts" variable was stored into the index.html file)
    # The domain name is not generated here.
    
    return render_template("composers/adapt/conceptmapper/conceptmapper.html", app_id = app_id)


@adapt_blueprint.route("/export/<app_id>/conceptmapper/domain.js")
def conceptmapper_domain(app_id):
    """
    conceptmapper_domain(app_id)
    This function points to the javascript file associated to an instance of the concept map.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.    
    @return: The javascript file with all its contents filled. Those contents are stored in the database. 
    """  
    
    #domain_orig = ["mass", "fluid", "density", "volume", "weight", "immersed object", "pressure", "force", "gravity", "acceleration", "Archimedes", "displacement", "equilibrium"]    

    app = get_app(app_id)
    
    data = json.loads(app.data)
    domain = data["concepts"]      

    return render_template("composers/adapt/conceptmapper/domain.js", domain = domain)    


@adapt_blueprint.route("/export/<app_id>/hypothesis/hypothesis.html")
def hypothesis_index(app_id):
    """
    hypothesis_index(app_id)
    This function points to the hypothesis tool instance.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.    
    @return: The webpage of a list of hypotheses.
    """   
        
    # In the templates, hypothesis.html points to {{ url_for('adapt.hypothesis_domain', app_id = app_id) }} 
    # instead of DomainTemplates.js
    # The domain name is not generated here.

    return render_template("composers/adapt/hypothesis/hypothesis.html", app_id = app_id)


@adapt_blueprint.route("/export/<app_id>/hypothesis/domain.js")
def hypothesis_domain(app_id):
    """
    hypothesis_domain(app_id)
    This function points to the javascript file associated to an instance of the hypothesis tool.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.    
    @return: The javascript file with all its contents filled. Those contents are stored in the database. 
    """  
    
    """    
    domain_orig = [
        {'text': 'IF', 'type': 'conditional'}, {'text': 'THEN', 'type': 'conditional'}, {'text': 'increases', 'type': 'conditional'}, 
        {'text': 'is larger than','type': 'conditional'}, {'text': 'is smaller than','type': 'conditional'}, {'text': 'decreases','type': 'conditional'}, 
        {'text': 'is equal to','type': 'conditional'}, {'text': 'remains','type': 'conditional'}, {'text': 'floats','type': 'output'}, 
        {'text': 'sinks','type': 'output'}, {'text': 'mass','type': 'input'}, {'text': 'fluid','type': 'input'}, 
        {'text': 'density','type': 'input'}, {'text': 'volume','type': 'input'}, {'text': 'weight','type': 'input'}, 
        {'text': 'immersed object','type': 'input'}, {'text': 'pressure','type': 'input'}, {'text': 'force','type': 'input'}, 
        {'text': 'gravity','type': 'input'}, {'text': 'acceleration','type': 'output'}, {'text': 'Archimedes principle','type': 'input'}, 
        {'text': 'submerge','type': 'input'}, {'text': 'float','type': 'output'}, {'text': 'displacement','type': 'input'}, {'text': 'equilibrium','type': 'output'}
    ]

    """    
    
    #json_str = domain_orig
    app = get_app(app_id)
    #update_app_data(app, domain_orig)
    domain = app.data   
    # We cannot prettify the JSON in this template because it is stored with other JS content
    return render_template("composers/adapt/hypothesis/domain.js", domain = domain)    


@adapt_blueprint.route("/export/<app_id>/edt/edt.html")
def edt_index(app_id):
    """
    hypothesis_index(app_id)
    This function points to the experiment design tool instance.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.    
    @return: The webpage of an experiment design.
    """  
    
    # In the templates, edt.html points to {{ url_for('adapt.edt_domain', app_id = app_id) }} 
    # instead of buoyancy.js
    # The domain name is also generated here.
    domain_name = 'buoyancy'
    experiment_name = 'Archimedes'
    return render_template("composers/adapt/edt/edt.html", app_id = app_id, domain_name = domain_name, experiment_name = experiment_name)


@adapt_blueprint.route("/export/<app_id>/edt/domain.js")
def edt_domain(app_id):
    """
    edt_domain(app_id)
    This function points to the javascript file associated to an instance of the experiment design tool.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.    
    @return: The javascript file with all its contents filled. Those contents are stored in the database. 
    """   
    
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


## Tests

@adapt_blueprint.route("/go", methods = ['GET', 'POST'])
def adapt_go():
    if request.method == "GET":    
        app_id = "1b5d3349-ef68-4774-a6d9-50c8ddeaa245"
        app = appstorage.get_app(app_id)
        
        
        data = json.loads(app.data)        
        concepts = data["concepts"]
        description = data["description"]
        return concepts
    return render_template("composers/adapt/index.html") 
