from flask import Blueprint, flash, json, redirect, render_template, request, session, url_for

import appcomposer.appstorage.api as appstorage

# Required imports for a customized app view for the adapt tool (a possible block to be refactored?)
from appcomposer.models import App
from appcomposer.babel import lazy_gettext
from appcomposer.login import current_user

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
from .edt import data as edt_data

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
    
    # TODO: request this to the API
    apps = App.query.filter_by(owner_id=current_user().id, composer='adapt').all()

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
            'name': unicode(name),
            'description': unicode(app_description),
            'adaptor_type': unicode(adaptor_type)
        }               

        #Dump the contents of the previous block and check if an app with the same name exists.
        # (TODO): do we force different names even if the apps belong to another adaptor type?
        app_data = json.dumps(data)

        try:
            app = appstorage.create_app(name, "adapt", app_data)
        except appstorage.AppExistsException:
            flash("An App with that name already exists", "error")
                        
            return render_template("composers/adapt/create.html", name=name, apps = apps, adaptor_type = adaptor_type, build_edit_link=build_edit_link)
        
        #Assign a unique identifier to the created app
        app_id =app.unique_id
                
        return redirect(url_for("adapt.adapt_edit", app_id = app_id))               


@adapt_blueprint.route("/edit/<app_id>/", methods = ['GET', 'POST'])
def adapt_edit(app_id):
    """
    adapt_edit()
    Form-based user interface for editing the contents of an adaptor app.
    @return: The final app with all its fields stored in the database.
    """        
    if not app_id:
        return "app_id not provided", 400
    app = appstorage.get_app(app_id)
    if app is None:
        return "App not found", 500

    # Common data to pass to the template (the URL only contains the app_id)
    data = json.loads(app.data)     
    name = data["name"]            
    adaptor_type = data["adaptor_type"]        

    # If a GET request is received, the page is shown.
    if request.method == "GET":        
        if adaptor_type == 'concept_map':
            # TODO: convert into plug-in
            return concept_map_data['load'](app, app_id, name, data)
        elif adaptor_type == 'hypothesis':
            # TODO: convert into plug-in
            return hypothesis_data['load'](app, app_id, name, data)
        elif adaptor_type == 'edt':
            # TODO: convert into plug-in
            return edt_data['load'](app, app_id, name, data)
        else:
            # TODO: what to do?
            return ":-("
    
    # If a POST request is received, the adaptor app is saved the database.    
    elif request.method == "POST":

        # SPECIFIC CONTROL STRUCTURE FOR THE SELECTED ADAPTOR TYPE --- TO CHANGE IN #74        
        if adaptor_type == 'concept_map':            
            # TODO: convert into plug-in
            return concept_map_data['edit'](app, app_id, name, data)
        elif adaptor_type == 'hypothesis':
            # TODO: convert into plug-in
            return hypothesis_data['edit'](app, app_id, name, data)
        elif adaptor_type == 'edt':
            # TODO: convert into plug-in
            return edt_data['edit'](app, app_id, name, data)
        else:
            # TODO: what to do?
            return ":-("

    
## Tests            

@adapt_blueprint.route("/more/<uuid_test>/", methods = ['GET', 'POST'])
def adapt_uuid(uuid_test):
    return uuid_test

"""
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html'), 404
"""
