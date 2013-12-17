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

# TODO: Register it or something
from .concept_map import data as concept_map_data
from .hypothesis import data as hypothesis_data

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

        # If the app data is empty (basic JSON schema), we are editing a new app. Otherwise, the data values are loaded from the database.
        if len(data) == 4:
                   
            return render_template("composers/adapt/edit.html", app=app, app_id = app_id, name = name, adaptor_type = adaptor_type, n_rows = 0)
        
        else:       
            if adaptor_type == 'concept_map':
                # TODO: convert into plug-in
                return concept_map_data['load'](app, app_id, name, data)
            
            elif adaptor_type == 'hypothesis':
                # TODO: convert into plug-in
                return hypothesis_data['load'](app, app_id, name, data)
            else:
                # Default number of rows for the experiment design -- GET REQUESTS
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
            appstorage.update_app_data(app, data)
            flash("Experiment design saved successfully", "success")

            return render_template("composers/adapt/edit.html", app=app, app_id = app_id, adaptor_type = adaptor_type, n_rows = 5)

            #flash(data, "success") 
            #flash(app.data, "success")  
            #-- DIFFERENCE between these two variables? First: single quotes. Second: double quotes      

            #return render_template("composers/adapt/edit.html", app=app, app_id = app_id, concepts = data["concepts"], conditionals = data["conditionals"], inputs = data["inputs"], outputs = data["outputs"]) 
    
## Tests            

@adapt_blueprint.route("/more/<uuid_test>/", methods = ['GET', 'POST'])
def adapt_uuid(uuid_test):
    return uuid_test

"""
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html'), 404
"""
