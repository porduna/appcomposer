from flask import Blueprint, render_template
import appcomposer.appstorage.api as appstorage

adapt_blueprint = Blueprint('adapt', __name__)

@adapt_blueprint.route("/")
def adapt_index():
    return render_template("composers/adapt/index.html")

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
    
    return render_template("composers/adapt/edt/domain.js", domain = domain, experiment = experiment)
