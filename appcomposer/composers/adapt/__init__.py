from flask import Blueprint, flash, json, redirect, render_template, request, session, url_for

from collections import OrderedDict
import appcomposer.appstorage.api as appstorage
from appcomposer.appstorage.api import create_app, get_app, update_app_data
from urlparse import urlparse

from forms import AdaptappCreateForm

# Required imports for a customized app view for the adapt tool (a possible block to be refactored?)
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose
from appcomposer.models import App
from appcomposer.babel import lazy_gettext
from itertools import izip

info = {
    'blueprint': 'adapt',
    'url': '/composers/adapt',

    'new_endpoint': 'adapt.adapt_index',   
    'edit_endpoint': 'adapt.adapt_edit',        
    'create_endpoint': 'adapt.adapt_create', 
    'delete_endpoint': 'dummy.delete',    

    'name': lazy_gettext('Adaptor Composer'),
    'description': lazy_gettext('Adapt an existing app.')
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
        if adaptor_type is None or len(adaptor_type) == 0:
            flash("adaptor_type not present", "error")

            # An adaptor_type is required.
            return redirect(url_for("adapt.adapt_index"))    

        # In order to show the list of apps we redirect to other url                                         
        return redirect(url_for("adapt.adapt_create", adaptor_type = adaptor_type))                   


@adapt_blueprint.route("/create/<adaptor_type>/", methods=["GET", "POST"])
def adapt_create(adaptor_type):
    """
    adapt_create()
    Loads the form for creating new adaptor apps and the list of adaptor apps from a specific type.
    @return: The app unique id.
    """    
    
    apps = App.query.filter_by(owner_id=1).all()     

    def build_edit_link(app):
        return url_for("adapt.adapt_edit", app_id=app.unique_id)  

    # If a get request is received, we just show the new app form and the list of adaptor apps    
    if request.method == "GET":               
                   
        if not adaptor_type:
            flash("adaptor_type not received", "error")            
            return "Missing parameters (Adaptor Type)", 400                     

        return render_template('composers/adapt/create.html', apps=apps, adaptor_type = adaptor_type, build_edit_link=build_edit_link) 
        #return render_template('composers/adapt/create.html', apps=apps, adaptor_type = adaptor_type) 

    # If a post is received, we are creating an adaptor app.
    elif request.method == "POST":

        # We read the app details provided by the user                        
        name = request.form["app_name"]
        app_description = request.form["app_description"]      
        adaptor_type = request.form["adaptor_type"]                               

        if name is None or len(name) == 0:
            flash("An application name is required", "error")
            return redirect(url_for("adapt.adapt_create", adaptor_type = adaptor_type))

        if app_description is None or len(app_description) == 0:
            app_description = "No description"
                 
        # Build the basic JSON schema of the adaptor app           
        data = {
            'adaptor_version': '1',
            'name': str(name),
            'description': str(app_description),
            'adaptor_type': str(adaptor_type)
        }               

        #Dump the contents of the previous block and check if an app with the same name exists.
        # (TODO): do we force different names even if the apps belong to another adaptor type?
        app_data = json.dumps(data)

        try:
            app = appstorage.create_app(name, "dummy", app_data)
        except appstorage.AppExistsException:
            flash("An App with that name already exists", "error")
                        
            return render_template("composers/adapt/create.html", name=name, apps = apps, adaptor_type = adaptor_type, build_edit_link=build_edit_link)
        
        #Assign a unique identifier to the created app
        app_id =app.unique_id
                
        return redirect(url_for("adapt.adapt_edit", app_id = app_id))               

        #return url_for("adapt.adapt_edit", app_id =app_id, _external=True)


@adapt_blueprint.route("/edit/<app_id>/", methods = ['GET', 'POST'])
def adapt_edit(app_id):
    """
    adapt_edit()
    Form-based user interface for editing the contents of an adaptor app.
    @return: The final app with all its fields stored in the database.
    """        
         
    # If a GET request is received, the page is shown.
    if request.method == "GET":        
                  
        if not app_id:
            return "app_id not provided", 400
        app = appstorage.get_app(app_id)
        if app is None:
            return "App not found", 500

        # Common data to pass to the template (the URL only contains the app_id)
        data = json.loads(app.data)     
        name = data["name"]            
        adaptor_type = data["adaptor_type"]        
        description = data["description"]                           
        n_rows = 0                                             

        # If the app data is empty (basic JSON schema), we are editing a new app. Otherwise, the data values are loaded from the database.
        if len(data) == 4:
                   
            return render_template("composers/adapt/edit.html", app=app, app_id = app_id, name = name, adaptor_type = adaptor_type, n_rows = n_rows)        
        
        else:       
            if adaptor_type == 'concept_map':
                
                concepts = data["concepts"]  
                return render_template("composers/adapt/edit.html", app=app, app_id = app_id, name = name, adaptor_type = adaptor_type, concepts = concepts)            
            
            elif adaptor_type == 'hypothesis':
                
                conditionals_stored = data["conditionals"]
                inputs_stored = data["inputs"]
                outputs_stored = data["outputs"]      

                # Format to load: inputs = [ {'text': 'immersed object','type': 'input'}, {'text': 'pressure','type': 'input'},... ]            
                def load_hypothesis_list(list_stored):
                    lst = []
                    for item in list_stored:
                        lst.append(item['text'])                
                    return lst     
                                     
                conditionals = load_hypothesis_list(conditionals_stored)
                inputs = load_hypothesis_list(inputs_stored)
                outputs = load_hypothesis_list(outputs_stored)
                        
                return render_template("composers/adapt/edit.html", app=app, app_id = app_id, name = name, adaptor_type = adaptor_type, conditionals = conditionals, inputs = inputs, outputs = outputs)            
            
            else:
                
                # Default number of rows for the experiment design -- GET REQUESTS
                n_rows = 5
                
              

                return render_template("composers/adapt/edit.html", app=app, app_id = app_id, name = name, adaptor_type = adaptor_type, x = x)                                                            
    
    # If a POST request is received, the adaptor app is saved the database.    
    elif request.method == "POST":
        
        app_id = request.form["app_id"]                                       
        
        # Select the app we're editing by its id.
        app = appstorage.get_app(app_id)                        
        
        # Common data to pass to the template (the URL only contains the app_id)
        data = json.loads(app.data)     
        name = str(data["name"])            
        adaptor_type = str(data["adaptor_type"])        
        description = str(data["description"])                           
        n_rows = 0                                             
        
        # SPECIFIC CONTROL STRUCTURE FOR THE SELECTED ADAPTOR TYPE --- TO CHANGE IN #74        
        if adaptor_type == 'concept_map':            
            '''
            data = {
                'adaptor_version': '1',
                'name': str(name),
                'description': str(app_description),
                'adaptor_type': str(adaptor_type),
                'concepts': list()}                         
            '''            
            # Retrieve the list of concepts and convert it to the format supported by the app.  
            # Request-- concepts: "a,b,c"  -> Concepts  (str): "a,b,c"               
      
            concepts = ', '.join(list(OrderedDict.fromkeys([ s.strip() for s in request.form["concepts"].split(',') ])))

            # Build the JSON of the current concept map.
            data = {
                "adaptor_version": 1,
                "name": name,
                "description": description,
                "adaptor_type": adaptor_type,
                "concepts": concepts}               
        
            appstorage.update_app_data(app, data)
            flash("Concept map saved successfully", "success")
            # flash(data["concepts"], "success")                      
                      
            return render_template("composers/adapt/edit.html", app=app, app_id = app_id, adaptor_type = adaptor_type, concepts = data["concepts"])
             
        elif adaptor_type == 'hypothesis':
            '''
            data = {
                'adaptor_version': '1',
                'name': str(name),
                'description': str(app_description),
                'adaptor_type': str(adaptor_type),
                'conditionals': list(), 
                'inputs': list(),
                'outputs': list()} 
            '''                                                       
            
            # Template values
            conditionals_values = request.form["conditionals"]             
            inputs_values = request.form["inputs"]
            outputs_values = request.form["outputs"]
            
            # Database manipulation
            conditionals_orig = request.form["conditionals"].split(',')         
            inputs_orig = request.form["inputs"].split(',') 
            outputs_orig = request.form["outputs"].split(',')
            
            
            # Conversion of the form input values to the hypothesis tool format below:
            # Request-- input_name = "input_type", value =  "a,b,c"  -> Output format = [ {'text':'a', 'type': 'input_type'}, {'text':'b', 'type': 'input_type', ...} ]
            def build_hypothesis_list(list_orig, element_type):
                lst = []
                for item in list_orig:
                    dic = { 'text': item, 'type': element_type}
                    lst.append(dic)                                 
                return lst

                            
            # A reserved word showed up.                        
            no_reserved = 'inputs'
            reserved_element_type = no_reserved[0:-1]
            
            inputs = build_hypothesis_list(inputs_orig, reserved_element_type)        
            outputs = build_hypothesis_list(outputs_orig, 'output') 
            conditionals = build_hypothesis_list(conditionals_orig, 'conditional')

            # Build the JSON of the current hypothesis tool.  
            data = {
                "adaptor_version": 1,
                "name": name,
                "description": description,
                "adaptor_type": adaptor_type,
                "conditionals": conditionals, 
                "inputs": inputs,
                "outputs": outputs} 

            appstorage.update_app_data(app, data)
            flash("Hypothesis saved successfully", "success")
            # flash(conditionals_orig, "success")

            return render_template("composers/adapt/edit.html", app=app, app_id = app_id, adaptor_type = adaptor_type, conditionals = conditionals_values, inputs = inputs_values, outputs = outputs_values)         
        
        else:
            '''
            # Experiment design tool monster specification. [!] name == domain name                                
            data = {
                'adaptor_version': '1',
                'name': str(name),
                'description': str(app_description),
                'adaptor_type': str(adaptor_type),
                'object properties': [{ 'name': str(objprop_name), 'type': str(objprop_type), 'symbol': str(objprop_symbol), 'unit': str(obj_propunit), 'obvalues': str(objprop_values) }],
                'object_relations':  [{ 'name': str(relname), 'object_properties':list(),'relation': str(relation) }], 
                'system_properties':  [{ 'name': str(sysprop_name), 'type':str(sysprop_type),'values': str(sysprop_values), 'symbol': str(sysprop_symbol), 'unit': str(sysprop_unit) }], 
                'object_measures': [{ 'name': str(objmeas_name), 'type': str(objmeas_type), 'values': list(), 'unit': str(objmeas_unit), 'depends_on': { 'object_properties': list(), 'system_properties': list() }} ],    

                # Warning: There can be more than one experiment stored here
                'expname': str(exp_name),
                'description': str(exp_description),
                'domain': str(domain_name),
                'object_property_selection': list(),
                'object_measure_selection': list(),
                'system_property_selection': list(),
                'object_property_specification': [ {'property': str(objpropspec_name),'initial': str(), 'unit': str(), 'values': list(), 'range': {'minimum': str(), 'maximum': str(), 'increment': str()}} ],
                'system_property_values': [ {'property': str(), 'value': str()} ]
            }                        
            '''
            
            # Default number of rows for the experiment design
            n_rows = 5       


            

          
            appstorage.update_app_data(app, data)
            flash("Experiment design saved successfully", "success")

            return render_template("composers/adapt/edit.html", app=app, app_id = app_id, adaptor_type = adaptor_type, n_rows = n_rows) 

            #flash(data, "success") 
            #flash(app.data, "success")  
            #-- DIFFERENCE between these two variables? First: single quotes. Second: double quotes      

            #return render_template("composers/adapt/edit.html", app=app, app_id = app_id, concepts = data["concepts"], conditionals = data["conditionals"], inputs = data["inputs"], outputs = data["outputs"]) 


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

@adapt_blueprint.route("/export/<app_id>/conceptmapper/app.xml")
def conceptmapper_widget(app_id):
    """
    conceptmapper_widget(app_id)
    This function points to the concept map instance.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.    
    @return: The webpage of a concept map.
    """  
        
    # In the templates, conceptmapper.html points to {{ url_for('adapt.conceptmapper_domain', app_id = app_id) }} 
    # instead of domain.js (In the original app, the "concepts" variable was stored into the index.html file)
    # The domain name is not generated here.
    
    return render_template("composers/adapt/conceptmapper/widget.xml", app_id = app_id)
    

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

    if len(data) == 4:    
        domain = json.dumps("empty")    
    else:    
        domain = json.dumps([ s.strip() for s in data["concepts"].split(',') ])

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

    #app = get_app(app_id)    

    return render_template("composers/adapt/hypothesis/hypothesis.html", app_id = app_id)

@adapt_blueprint.route("/export/<app_id>/hypothesis/app.xml")
def hypothesis_widget(app_id):
    """
    hypothesis_widget(app_id)
    This function points to the hypothesis instance.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.    
    @return: The webpage of a concept map.
    """  
        
    # In the templates, hypothesis.html points to {{ url_for('adapt.hypothesis_domain', app_id = app_id) }} 
    # instead of domain.js (In the original app, the "concepts" variable was stored into the index.html file)
    # The domain name is not generated here.
    
    return render_template("composers/adapt/hypothesis/widget.xml", app_id = app_id)


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
    
    app = get_app(app_id)
    
    data = json.loads(app.data)
    conditionals = data["conditionals"] 
    inputs = data["inputs"] 
    outputs = data["outputs"]

    domain = json.dumps(conditionals + inputs + outputs)
    
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


@adapt_blueprint.route("/export/<app_id>/edt/app.xml")
def edt_widget(app_id):
    """
    edt_widget(app_id)
    This function points to the edt instance.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.    
    @return: The webpage of a edt.
    """  
        
    # In the templates, conceptmapper.html points to {{ url_for('adapt.edt_domain', app_id = app_id) }} 
    # instead of domain.js (In the original app, the "concepts" variable was stored into the index.html file)
    # The domain name is not generated here.
    
    return render_template("composers/adapt/edt/widget.xml", app_id = app_id)
    

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

@adapt_blueprint.route("/more/<uuid_test>/", methods = ['GET', 'POST'])
def adapt_uuid(uuid_test):
    return uuid_test

"""
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html'), 404
"""
