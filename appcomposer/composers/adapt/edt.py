import json
from collections import OrderedDict, Counter
from flask import render_template, request, flash
import appcomposer.appstorage.api as appstorage

from appcomposer.composers.adapt import adapt_blueprint

def edt_load(app, app_id, name, data):
    
    # Uncomment these lines for normal behavior. TODO
    #If appdata has four items, we are editing an empty experiment design    
    # if len(data) == 4:
    #    return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, n_trows = 4, emptycontent_trows = [1,2,3], nstep = 2)


    #Otherwise, the data values are loaded from the database.
    columns_objprops = {"name":["mass", "volume", "density","material", "shape"], "type": ["n", "n", "n", "y", "y"], "symbol": ["m", "V", "rho","",""], "unit": ["kg", "m^3", "kg / m^3","",""], "allvalues": ["", "", "","*","*"]}
    columns_sysprops = {"name":["fluid_aquarium", "fluid_density", "fluid_column"], "type": ["y", "y", "y"], "symbol": ["", "rho", "h"], "unit": ["", "kg / m^3", "m"], "allvalues": ["*", "", ""]}            
                    
    object_properties = zip(columns_objprops["name"], columns_objprops["type"], columns_objprops["symbol"], columns_objprops["unit"], columns_objprops["allvalues"])
    system_properties = zip(columns_sysprops["name"], columns_sysprops["type"], columns_sysprops["symbol"], columns_sysprops["unit"], columns_sysprops["allvalues"])

    #Original: object_relations = [{"name": "density", "object_properties": [ "density", "mass", "volume" ], "relation": "density = mass / volume"}]
    columns_objrels = {"name":["mass","volume","density","material","shape"], "relation": ["","","mass / volume","",""]}
    object_relations = zip(columns_objrels["name"], columns_objrels["relation"])
        
    object_measures_formatted = [
            {"name": "water_displacement", "type": "magnitude", "unit": "m^3", "depends_on": { "object_properties": ["mass"], "system_properties": ["fluid_density"]}},
            {"name": "sink_or_float", "type": "multitude", "values": ["sinks", "floats"], "depends_on": { "object_properties": ["density"], "system_properties": ["fluid_density"]}}
    ] 
    
    columns_objmeasu = {"name":["water_displacement", "sink_or_float"], "type": ["n", "n"], "values": ["", "sinks, floats"], "unit": ["m^3", ""]}   
    #putada: en object measures se puede asignar una misma system property o object property a dos medidas diferentes. Permitimos guardar vaues separados por comas    
    object_measures = zip(columns_objmeasu['name'], columns_objmeasu['type'], columns_objmeasu['values'], columns_objmeasu['unit'])    

    object_measures_names = ["water_displacement","sink_or_float"]

    #Experiment data
    experiment_name = "Archimedes" #campo propio en el json
    experiment_description = "Simulation-based version of the buoyancy experiment" #idem
    experiment_domain = "buoyancy" #experiment_domain = name (domain)

    object_property_selection = ["mass", "volume", "shape"]
    object_measure_selection = ["sink_or_float", "water_displacement"]
    system_property_selection = ["fluid_aquarium"]
    
    # We will show all object properties and discard fields with empty values (initial = "")
    columns_objprops_spec ={"property_name": ["mass", "volume", "shape"], "initial": ["300", "200", "sphere"], "unit": ["gram", "cm_3", ""], "minimum": [ "50", "50", ""], "maximum": ["500", "500", ""], "increment": ["50", "50", ""], "values": ["", "", "sphere, cube"]}
    object_property_specification = zip(columns_objprops_spec["property_name"], columns_objprops_spec["initial"], columns_objprops_spec["unit"], 
                                                            columns_objprops_spec["minimum"], columns_objprops_spec["maximum"], columns_objprops_spec["increment"], columns_objprops_spec["values"])

    columns_sysprop_values = {"property_name": ["fluid_aquarium", "density"], "value": ["water", "1.0"]}
    system_property_values = zip(columns_sysprop_values["property_name"], columns_sysprop_values["value"])
    
    #aaaaand, it's done. Next: validation and verifying that the user enters duplicated values (when it's not allowed)
    
    return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, name = name, 
            object_properties = object_properties, system_properties = system_properties, object_measures = object_measures, object_relations = object_relations,
            experiment_name = experiment_name, experiment_description = experiment_description,  experiment_domain = experiment_domain,
            object_property_selection = object_property_selection, object_measure_selection = object_measure_selection, object_measures_names = object_measures_names, 
            system_property_selection = system_property_selection, object_property_specification = object_property_specification, 
            system_property_values = system_property_values, n_trows = 21)    


def edt_edit(app, app_id, name, data):
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
                               
    # Steps for the experiment design editor    
    # If the app data is empty (basic JSON schema), we are editing a new app. Otherwise, the data values are loaded from the database.
    if len(data) == 4:       

        # 1st step: Domain 1 of 2
        # Template values to retrieve: Object properties & System properties
        objprop_names = request.form.getlist('objprop_name')             
        objprop_symbols = request.form.getlist('objprop_symbol')                        
        objprop_units = request.form.getlist('objprop_unit')
        objprop_values = request.form.getlist('objprop_value')                     

        ### MISSING CHECKBOXES ###########
        #objprop_types = request.form.getlist('objprop_type')
        #objprop_avs = request.form.getlist('objprop_av')                                                      

        sysprop_names = request.form.getlist('sysprop_name') 

        ### MISSING CHECKBOXES ###########
        #sysprop_types = request.form.getlist('sysprop_type')

        sysprop_symbols = request.form.getlist('sysprop_symbol') 
        sysprop_units = request.form.getlist('sysprop_unit')                
        sysprop_values = request.form.getlist('sysprop_value') 

        #multimulti = request.form.getlist('measures_selection')        
        multimulti = request.form.getlist('objprop_type')   

        # Build the JSON of the current experiment design (1st step). [!] name = domain name  

        print multimulti

        return "ok"
        #return render_template("composers/adapt/edit.html", app=app, app_id = app_id, nstep = 2) 

    elif len(data) == 15: 

        data = json.loads(app.data) # IS THIS NECESSARY?
        objprop_names = data["objprop_names"]
        # 2nd step: Domain 2 of 2
        # Template values to retrieve: Object relations & Object measures. [!] objprop_relname must be one of the objprop_names
        objprop_relnames = request.form.getlist('objprop_relname')
        objprop_relations = request.form.getlist('objprop_relation')                    

        ### MISSING CHECKBOXES ###########
        #objproptype_list = request.form.getlist('objprop_type')
        #objpropavail_list = request.form.getlist('objprop_avail')                                                      


        # Build the JSON of the current experiment design (2nd step).

        ############ Verify how to keep previous fields before updating with the appstorage API
        data.update({        
            'objprop_relnames':objprop_relnames,
            'objprop_relations':objprop_relations,
            
            'measure_names': measure_names, 
            'measure_types': measure_types,
            'measure_units': measure_units,
            'measure_dependencies': measure_dependencies                       
        }) #new data length = 21

        appstorage.update_app_data(app, data)
        flash("Domain properties [2] saved successfully", "success")
        # flash(objprop_names, "success")
                    
        return render_template("composers/adapt/edit.html", app=app, app_id = app_id, nstep = 3)      

    elif len(data) == 21:

        data = json.loads(app.data)

        # 3rd step: Experiment
        # Template values to retrieve: Experiment values. [!] An experiment must be associated with a domain
        objprop_relnames = request.form.getlist('objprop_relname')
        objprop_relations = request.form.getlist('objprop_relation')                    

        ### MISSING CHECKBOXES ###########
        #objproptype_list = request.form.getlist('objprop_type')
        #objpropavail_list = request.form.getlist('objprop_avail')                                                      


        # Build the JSON of the current experiment design (3rd step).

        ############ Figure out how to send only the new keys to the appstorage API
        data.update({             
            ### EXPERIMENT DATA - Unique?
            'experiment_name': experiment_name,
            'experiment_description': experiment_description,
            'associated_domain': associated_domain,
            'objprops_selection': objprops_selection,
            'measures_selection': measures_selection,
            'sysprops_selection': sysprops_selection,
            
            'exp_properties':exp_properties,
            'exp_objprop_units':exp_objprop_units,
            'exp_objprop_initials':exp_objprop_initials, 
            'exp_objprop_values':exp_objprop_values, 
            'exp_objprop_mins':exp_objprop_mins, 
            'exp_objprop_maxs':exp_objprop_maxs,                                                                                                     
            'exp_objprop_increments':exp_objprop_increments, 
            'exp_sysprops':exp_sysprops,                                                                
            'exp_syspropsvalues':exp_syspropsvalues,                    
        }) #new data length = 36

        appstorage.update_app_data(app, data)
        flash("Experiment values saved successfully", "success")
        # flash(experiment_name, "success")
                    
        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, nstep = 4)      

    else:
        return "Error"                     


#
# Auxiliar routes
#

@adapt_blueprint.route("/export/<app_id>/edt/edt.html")
def edt_index(app_id):
    """
    edt_index(app_id)
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



data = {
    'initial' : lambda : {},
    'load' : edt_load,
    'edit' : edt_edit,
    'name' : 'Experiment Design Tool',
    'id'   : 'edt',
}
