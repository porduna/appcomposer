import json
from collections import OrderedDict, Counter
from flask import render_template, request, flash
import appcomposer.appstorage.api as appstorage

from appcomposer.composers.adapt import adapt_blueprint

def edt_load(app, app_id, name, data):
    #Data values are loaded from the database.
    
    if len(data) == 4:
        #If appdata has four items, we are viewing an empty experiment design (Domain 1 of 2).
        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, n_trows = len(data), emptycontent_trows = [1,2,3])
    
    elif len(data) == 7:
        # Viewing Domain 2 of 2. 1 of 2 is loaded from the DB.
        #Reading the current values and storing them in lists -  these loops will be used with the other variables to build the columns
        objprops_names = []; objprops_types = []; objprops_symbols = []; objprops_units = []; objprops_allvalues = [];
        sysprops_names = []; sysprops_types = []; sysprops_symbols = []; sysprops_units = []; sysprops_allvalues = [];
        objmeasu_names = []; objmeasu_types = []; objmeasu_units = []; objmeasu_values = [];
        for item in data["object_properties"]:
            objprops_names.append(item["name"])
            objprops_types.append(item["type"])
            objprops_allvalues.append(item["values"])
            #WARNING: the "symbol", "unit" items do not exist when multitude is selected & "values"" is not present in magnitude
            if "symbol" in item:
                objprops_symbols.append(item["symbol"])            
            else: 
                objprops_symbols.append("")
            if "unit" in item:
                objprops_units.append(item["unit"])
            else:
                objprops_units.append("")        
            #if "values" in item:
            #    objprops_allvalues.append("values")
            #else:
            #    objprops_allvalues.append("")

        for item in data["system_properties"]:
            sysprops_names.append(item["name"])
            sysprops_types.append(item["type"])
            sysprops_allvalues.append(item["values"])
            #Same here
            if "symbol" in item:            
                sysprops_symbols.append(item["symbol"])
            else:
                sysprops_symbols.append("")
            if "unit" in item:
                sysprops_units.append(item["unit"])
            else:
                sysprops_units.append("")
            #if "values" in item:
            #    sysprops_allvalues.append("values")
            #else:
            #    sysprops_allvalues.append("")        

        for item in data["object_measures"]:
            objmeasu_names.append(item["name"])
            objmeasu_types.append(item["type"])
            objmeasu_values.append(item["values"][0]) #FIX THIS!!!!!!!!!!!!!!!!!!
            #Same here
            if "unit" in item:
                objmeasu_units.append(item["unit"])
            else:
                objmeasu_units.append("")            
            #if "values" in item:
            #    objmeasu_values.append("values")
            #else:
            #    objmeasu_values.append("")

        # Template values
        columns_objprops = {"name": objprops_names, "type": objprops_types, "symbol": objprops_symbols, "unit": objprops_units, "allvalues": objprops_allvalues}
        columns_sysprops = {"name":sysprops_names, "type": sysprops_types, "symbol": sysprops_symbols, "unit": sysprops_units, "allvalues": sysprops_allvalues}            
        columns_objmeasu = {"name":objmeasu_names, "type": objmeasu_types, "unit": objmeasu_units,  "values": objmeasu_values}
        
        object_properties = zip(columns_objprops["name"], columns_objprops["type"], columns_objprops["symbol"], columns_objprops["unit"], columns_objprops["allvalues"])
        system_properties = zip(columns_sysprops["name"], columns_sysprops["type"], columns_sysprops["symbol"], columns_sysprops["unit"], columns_sysprops["allvalues"])
        object_measures = zip(columns_objmeasu['name'], columns_objmeasu['type'], columns_objmeasu['unit'], columns_objmeasu["values"])  
        
        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, n_trows = len(data), 
                                                object_properties = object_properties, system_properties = system_properties, object_measures = object_measures, emptycontent_trows = [1,2,3])
    
    elif len(data) == 9:
        
        # Viewing empty Experiment 1 of 2. Domain 2 of 2 data is loaded from the DB.
        objrels_names = []; objrels_relations = [];
        for item in data["object_relations"]:
            objrels_names.append(item["name"])
            objrels_relations.append(item["relation"])
            # objrels_varlist.append(item["object_properties"])

            object_relations = zip(objrels_names, objrels_relations)            

            dependencies = [
                    {"name": "water_displacement", "depends_on": { "object_properties": ["mass","density"], "system_properties": ["fluid_density"]}},
                    {"name": "sink_or_float", "depends_on": { "object_properties": ["density"], "system_properties": ["fluid_density"]}}
                ]

            #Comparison: list of all object/system properties with the selected by the user
            #dependencies_selected = [""] - with set : get selected and not selected
            # if the user has nothing selected in a row: validation - you must select one           

        print data["object_measures"]

        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, n_trows = len(data), emptycontent_trows = [1,2,3],  object_relations = object_relations,
                                                object_properties = data["object_properties"], object_measures = data["object_measures"], system_properties = data["system_properties"],)
    
    elif len(data) == 10:
        # Viewing Empty Experiment 2 of 2. Experiment 1 of 2 is loaded from the DB.
        
        experiment_name = data["exp-0"]["name"]
        experiment_description = data["exp-0"]["description"]

        #object_property_selection = ["mass", "volume", "shape"]
        #object_measure_selection = ["sink_or_float", "water_displacement"]    ** FIXXX!!! GENERATE SELECTED + NOT SELECTED OPTIONS FROM THE LISTS
        #system_property_selection = ["fluid_aquarium"]
        
        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, n_trows = len(data), experiment_name = experiment_name, experiment_description = experiment_description,
                                                    object_property_selection = data["exp-0"]["object_property_selection"], system_property_selection = data["exp-0"]["system_property_selection"],
                                                    object_measure_selection = data["exp-0"]["object_measure_selection"])
    
    elif len(data) == 11:
        # Q&A: Do we load all data variables? There are dependencies between tabs...
        experiment_name = data["exp-0"]["name"]
        experiment_description = data["exp-0"]["description"]
        print data
        
        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, n_trows = len(data), experiment_name = experiment_name, experiment_description = experiment_description,
                                                object_property_selection = data["exp-0"]["object_property_selection"], system_property_selection = data["exp-0"]["system_property_selection"], 
                                                object_property_specification = data["exp-0"]["object_property_specification"], system_property_values = data["exp-0"]["system_property_values"],
                                                object_measure_selection = data["exp-0"]["object_measure_selection"])

    else:
        return "Error"

def edt_edit(app, app_id, name, data):                               
    # Steps for the experiment design editor    
    # If the app data is empty (basic JSON schema), we are editing a new edt app.
    if len(data) == 4:       

        # 1st step: Domain 1 of 2
        # Values to retrieve: Object properties, System properties & Object measures
        objprop_names = request.form.getlist('objprop_name')
        objprop_types = request.form.getlist('objprop_type')
        objprop_symbols = request.form.getlist('objprop_symbol')
        objprop_units = request.form.getlist('objprop_unit')
        objprop_values = request.form.getlist('objprop_value')

        sysprop_names = request.form.getlist('sysprop_name')
        sysprop_types = request.form.getlist('sysprop_type')
        sysprop_symbols = request.form.getlist('sysprop_symbol')
        sysprop_units = request.form.getlist('sysprop_unit')
        sysprop_values = request.form.getlist('sysprop_value')

        objmeasu_names = request.form.getlist('measure_name')
        objmeasu_types = request.form.getlist('measure_type')
        objmeasu_units = request.form.getlist('measure_unit')
        objmeasu_values = request.form.getlist('measure_value')

        #Build the object_properties data field
        result_obj = {}; object_properties = [];
        
        for element in range(len(objprop_names)):
            result_obj = {"name":objprop_names[element], "type": objprop_types[element], "symbol": objprop_symbols[element], "unit": objprop_units[element], "values": objprop_values[element]}
            object_properties.append(result_obj)

        #Build the system_properties data field
        result_sys = {}; system_properties = [];
        
        for element in range(len(sysprop_names)):
            result_sys = {"name":sysprop_names[element], "type": sysprop_types[element], "symbol": sysprop_symbols[element], "unit": sysprop_units[element], "values": sysprop_values[element]}
            system_properties.append(result_sys)

        #"object_measures": [
        #    {"name": "water_displacement", "type": "magnitude", "unit": "m^3"},
        #    {"name": "sink_or_float", "type": "multitude", "values": ["sinks", "floats"]}
        #]
        
        result_measu = {}; object_measures = [];

        objvalues = []
        # Conversion: objmeasu_values (comma separated list) -> objvalues (list of values)
        for item in objmeasu_values:
            objvalues.append(item.split(','))

        #Build the object_measures data field
        for element in range(len(objmeasu_names)):
            #result_measu = {"values": objvalues[element]}  #AAARGGGGH VALUES IS LIST
            result_measu = {"name":objmeasu_names[element], "type": objmeasu_types[element], "unit": objmeasu_units[element], "values": objvalues[element]}
            object_measures.append(result_measu)

        #Update the data dictionary of the step 1.
        data.update({
            "object_properties": object_properties,
            "system_properties": system_properties,
            "object_measures": object_measures})

        # Template values:
        columns_objprops = {"name": objprop_names, "type": objprop_types, "symbol": objprop_symbols, "unit": objprop_units, "allvalues": objprop_values}
        columns_sysprops = {"name":sysprop_names, "type": sysprop_types, "symbol": sysprop_symbols, "unit": sysprop_units, "allvalues": sysprop_values}            
        columns_objmeasu = {"name":objmeasu_names, "type": objmeasu_types, "unit": objmeasu_units,  "values": objmeasu_values}
        
        object_properties_tabbed = zip(columns_objprops["name"], columns_objprops["type"], columns_objprops["symbol"], columns_objprops["unit"], columns_objprops["allvalues"])
        system_properties_tabbed = zip(columns_sysprops["name"], columns_sysprops["type"], columns_sysprops["symbol"], columns_sysprops["unit"], columns_sysprops["allvalues"])
        
        object_measures_tabbed = zip(columns_objmeasu['name'], columns_objmeasu['type'], columns_objmeasu['unit'], columns_objmeasu['values'])  

        appstorage.update_app_data(app, data)
        flash("Domain *1 of 2* saved successfully", "success")

        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, object_properties = object_properties_tabbed, system_properties = system_properties_tabbed, object_measures = object_measures_tabbed,
                                                emptycontent_trows = [1,2,3], n_trows = len(data)) 
    
    elif len(data) == 7: 
        
        #objprop_names = data["objprop_names"]
        # 2nd step: Domain 2 of 2
        # Template values to retrieve: Object relations & Object measures. [!] objprop_relname must be one of the objprop_names
        #Begin of Domain 2 of 2. Note: The object_system_dependencies list is created ad-hoc for validation (in the JSON schema it is included into object_relations)

        objprop_on = []; objprop_vars = []; objprop_relations = [];
        objprop_relnames = request.form.getlist('objprop_relname')
        
        # Retrieve the lists of values
        for item in range(1, len(objprop_relnames)+1):
            objprop_on.append(request.form["optionRadioOn-"+str(item)])
            objprop_vars.append(request.form.getlist("objprop_var-"+str(item)))
            objprop_relations.append(request.form["objprop_relation-"+str(item)])

        # Lists of Object dependencies & System dependencies
        objmeasu_sets = request.form.getlist('objmeasu_set')
        object_measures = data["object_measures"]
        objprop_deps = []; sysprop_deps = [];
        # Retrieve the lists of values of object dependencies ("objprop_dep-1" to "objprop_dep-n")
        for item in range(1, len(object_measures)+1):            
            objprop_deps.append(request.form.getlist("objprop_dep-"+str(item)))
            sysprop_deps.append(request.form.getlist("sysprop_dep-"+str(item)))

        #Build the object_relations data field
        result_obj = {}; object_relations = [];
        
        for element in range(len(objprop_relnames)):
            result_obj = {"name":objprop_relnames[element], "object_properties": objprop_vars[element], "relation": objprop_relations[element]}
            object_relations.append(result_obj)

        #Build the object_system_dependencies data field
        result_objsys = {}; object_system_dependencies = [];
        
        for element in range(len(object_measures)):
            result_objsys = {"name":object_measures[element], "dependson": { "object_properties": objprop_deps[element], "system_properties": sysprop_deps[element] }}
            object_system_dependencies.append(result_objsys)

        # Build the JSON of the current experiment design (2nd step).
        data.update({        
            "object_relations":object_relations,
            "object_system_dependencies":object_system_dependencies                   
        })

        appstorage.update_app_data(app, data)
        
        flash("Domain properties *2 of 2* saved successfully", "success")     

        # Template values
        measu_names = []
        for item in object_measures:
            measu_names.append(item["name"])        
        
        columns_rels = {"name": objprop_relnames, "dependson": objprop_vars, "relation": objprop_relations}
        columns_deps = {"name":measu_names, "obj_deps": objprop_deps, "sys_deps": sysprop_deps}
        
        rels_tabbed = zip(columns_rels["name"], columns_rels["dependson"], columns_rels["relation"])
        deps_tabbed = zip(columns_deps["name"], columns_deps["obj_deps"], columns_deps["sys_deps"])       

        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, object_measures = object_measures, object_relations = rels_tabbed, 
                                                    object_properties = data["object_properties"], system_properties = data["system_properties"], dependencies = deps_tabbed, n_trows = len(data)) 

    elif len(data) == 9:

        # 3rd step: Experiment 1 of 2
        # Template values to retrieve: Experiment values. [!] An experiment must be associated with a domain                   

        experiment_name = request.form["experiment_name"]
        experiment_description = request.form["experiment_description"]
        experiment_domain = data["name"] # Hidden for now. Do we need a system to manage them?
        objprops_selection = request.form.getlist('objprops_selection')
        measures_selection = request.form.getlist('measures_selection')
        sysprops_selection = request.form.getlist('sysprops_selection')

        # Build the JSON of the current experiment design (Experiment 1 of 2). Experiment ID - Unique?
        data.update({
            "exp-0" : {
                # This variable stores all the information required for the experiment
                'name': experiment_name,
                'description': experiment_description,
                'domain': experiment_domain,
                'object_property_selection': objprops_selection,
                'object_measure_selection': measures_selection,
                'system_property_selection': sysprops_selection
            }
        }) #new data length = 10

        appstorage.update_app_data(app, data)
        flash("Experiment *1 of 2* saved successfully", "success")
                    
        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, experiment_name = experiment_name, experiment_description = experiment_description,
                                                objprops_selection = objprops_selection, measures_selection = measures_selection, system_property_selection = sysprops_selection, n_trows = len(data))      

    elif len(data) == 10:

        # 4th step: Experiment 2 of 2
        object_property_selection = data["exp-0"]["object_property_selection"]
        system_property_selection = data["exp-0"]["system_property_selection"]
        object_measure_selection = data["exp-0"]["object_measure_selection"]
        
        experiment_name = data["exp-0"]["name"] ### FIXX THIS!!!
        experiment_description = data["exp-0"]["description"]
        experiment_domain = data["exp-0"]["domain"]
        
        # Object property values
        exprop_initials = request.form.getlist('exprop_initial')
        exprop_units = request.form.getlist('exprop_unit')
        exprop_mins = request.form.getlist('exprop_min')
        exprop_maxs = request.form.getlist('exprop_max')
        exprop_increments = request.form.getlist('exprop_increment')
        
        exprop_values = request.form.getlist('exprop_value')

        # System property values
        exp_sysprop_values = request.form.getlist('exp_sysprop_value')

        #Build the object property specification data field
        result_objpropspec = {}; object_property_specification = [];
        
        for element in range(len(object_property_selection)):
            result_objpropspec = {"property": object_property_selection[element], "initial": exprop_initials[element], "unit": exprop_units[element], 
                                                "range": {"minimum": exprop_mins[element], "maximum": exprop_maxs[element], "increment": exprop_increments[element], "values": exprop_values[element]}}
            object_property_specification.append(result_objpropspec)

        #Build the system property values data field
        result_syspropval = {}; system_property_values = [];
        for element in range(len(system_property_selection)):
            result_syspropval = {"property": system_property_selection[element], "value": exp_sysprop_values[element]}
            system_property_values.append(result_syspropval)
        
        # Build the JSON of the current experiment design (Experiment 2 of 2)
    
        data.update({
            "exp-0" : {
                # This variable stores all the information required for the experiment
                'name': experiment_name,
                'description': experiment_description,
                'domain': experiment_domain,
                'object_property_selection': object_property_selection,
                'object_measure_selection': object_measure_selection,
                'system_property_selection': system_property_selection,
                
                'object_property_specification': object_property_specification,
                'system_property_values': system_property_values
            },
            "finished": True
        }) #new data length = 11

        appstorage.update_app_data(app, data)
        flash("Experiment *2 of 2* saved successfully", "success")

        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, n_trows = len(data), object_property_selection = object_property_selection, system_property_selection = system_property_selection,
                                                object_property_specification = object_property_specification, system_property_values = system_property_values, experiment_name = experiment_name, experiment_description = experiment_description)

    elif len(data) == 11: # Pending task: What can the user edit in the final EDT? The code of the last tab could be merged with the previous block.
        
        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, n_trows = len(data),
                                                object_property_selection = data["exp-0"]["object_property_selection"], system_property_selection = data["exp-0"]["system_property_selection"], 
                                                object_property_specification = data["exp-0"]["object_property_specification"], system_property_values = data["exp-0"]["system_property_values"])
    
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

    app = appstorage.get_app(app_id)
    data = json.loads(app.data)
    
    domain_name = data['name']
    experiment_name = data['exp-0']['name']
    return render_template("composers/adapt/edt/edt.html", app_id = app_id, domain_name = domain_name, experiment_name = experiment_name)


@adapt_blueprint.route("/export/<app_id>/edt/app.xml")
def edt_widget(app_id):
    """
    edt_widget(app_id)
    This function points to the edt instance.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.
    @return: The webpage of a edt.
    """

    return render_template("composers/adapt/edt/widget.xml", app_id = app_id)


@adapt_blueprint.route("/export/<app_id>/edt/domain.js")
def edt_domain(app_id):
    """
    edt_domain(app_id)
    This function points to the javascript file associated with an instance of the experiment design tool.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.
    @return: The javascript file with all its contents filled. Those contents are stored in the database.
    """

    # Selected experiment = data["exp-0"]...

    app = appstorage.get_app(app_id)
    data = json.loads(app.data)

    domain = {
        # This variable stores all the information required for the domain
        'name': data['name'],
        'description': data['description'],
        'object_properties': data['object_properties'],
        'object_relations': data['object_relations'],
        'system_properties': data['system_properties'],
        'object_measures': data['object_measures'] 
    }
    
    experiment = {
        # This variable stores all the information required for the experiment
        'name': data['exp-0']['name'],
	    'description': data['exp-0']['description'],
	    'domain': data['exp-0']['domain'],
	    'object_property_selection': data['exp-0']['object_property_selection'],
	    'object_measure_selection': data['exp-0']['object_measure_selection'],
	    'system_property_selection': data['exp-0']['system_property_selection'],
	    'object_property_specification': data['exp-0']['object_property_specification'],
	    'system_property_values': data['exp-0']['system_property_values']
    }

    aloha = json.dumps(experiment, indent = 4)
    print aloha

    return render_template("composers/adapt/edt/domain.js", domain = json.dumps(domain, indent = 4, sort_keys=True), experiment = json.dumps(experiment, indent = 4, sort_keys=True),
                                            domain_name = data['name'], experiment_name = data['exp-0']['name'])



data = {
    'initial' : lambda : {},
    'load' : edt_load,
    'edit' : edt_edit,
    'name' : 'Experiment Design Tool',
    'id'   : 'edt',
}
