import json
from flask import render_template, flash
from appcomposer.composers.adapt import adapt_blueprint
import appcomposer.appstorage.api as appstorage

def edt_new():
    return

def edt_load(app, app_id, name, data):
    # If the app data is empty (basic JSON schema), we are editing a new app. Otherwise, the data values are loaded from the database.
    if len(data) == 4:
        return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, name = name, n_rows = 0)

    return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, name = name)

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

    # Default number of rows for the experiment design
    appstorage.update_app_data(app, data)
    flash("Experiment design saved successfully", "success")

    return render_template("composers/adapt/edt/edit.html", app=app, app_id = app_id, n_rows = 5)


#
# Auxiliar routes
#

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



data = {
    'new'  : edt_new,
    'load' : edt_load,
    'edit' : edt_edit,
    'id'   : 'edt',
}
