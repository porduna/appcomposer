import json
from flask import render_template

from appcomposer.composers.adapt import create_adaptor

adaptor = create_adaptor('Experiment Design Tool')

@adaptor.edit_route
def edit(app_id):
    data = adaptor.load_data(app_id)
    name = data["name"]

    return render_template("edt/edit.html", app_id = app_id, name = name)


#
# Auxiliar routes
#

@adaptor.route("/export/<app_id>/edt/edt.html")
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
    return render_template("edt/edt.html", app_id = app_id, domain_name = domain_name, experiment_name = experiment_name)


@adaptor.route("/export/<app_id>/edt/app.xml")
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

    return render_template("edt/widget.xml", app_id = app_id)


@adaptor.route("/export/<app_id>/edt/domain.js")
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

    return render_template("edt/domain.js", domain = json.dumps(domain, indent = 4), experiment = json.dumps(experiment, indent = 4))

