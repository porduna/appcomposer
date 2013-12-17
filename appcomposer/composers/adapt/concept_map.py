import json
from flask import render_template

from appcomposer.composers.adapt import adapt_blueprint

def concept_map_new():
    pass

def concept_map_load(app, app_id, name, data):
    # If the app data is empty (basic JSON schema), we are editing a new app. Otherwise, the data values are loaded from the database.
    if len(data) == 4:
        return render_template("composers/adapt/conceptmapper/edit.html", app=app, app_id = app_id, name = name, n_rows = 0)

    concepts = data["concepts"]
    return render_template("composers/adapt/conceptmapper/edit.html", app=app, app_id = app_id, name = name, concepts = concepts)

# Auxiliar routes


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


# 
# Data structure (for registering)
# 

data = {
   'version' : 1,
   'new' : concept_map_new,
   'load' : concept_map_load,
   'id' : 'edt',
}
