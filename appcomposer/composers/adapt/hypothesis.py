from flask import render_template
from appcomposer.composers.adapt import adapt_blueprint


def hypothesis_new():
    pass

def hypothesis_load(app, app_id, name, data):
    # If the app data is empty (basic JSON schema), we are editing a new app. Otherwise, the data values are loaded from the database.
    if len(data) == 4:
        return render_template("composers/adapt/hypothesis/edit.html", app=app, app_id = app_id, name = name, n_rows = 0)

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
            
    return render_template("composers/adapt/hypothesis/edit.html", app=app, app_id = app_id, name = name, adaptor_type = adaptor_type, conditionals = conditionals, inputs = inputs, outputs = outputs)            

# 
# Auxiliar routes
# 

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





# 
# Data structure (for registering)
# 

data = {
   'version' : 1,
   'new' : hypothesis_new,
   'load' : hypothesis_load,
   'id' : 'edt',
}
