import json
from collections import OrderedDict
from flask import abort, make_response, render_template, request, flash

from appcomposer.composers.adapt import create_adaptor

#This is required by the config web service (check if app_id exists). Can we use the url_for('.edit') method without repeating code?
import appcomposer.appstorage.api as appstorage

adaptor = create_adaptor('Concept Mapper', {
        'debug' : 'true',
        'actionlogging' : 'consoleShort',
        'show_prompts' : 'true',
        'textarea_concepts' : 'true',
        'combobox_concepts' : 'true',
        'drop_external' : 'true',
        'concepts' : '',
        'relations' : ''
   })


@adaptor.edit_route
def edit(app_id):
    data = adaptor.load_data(app_id)
    concepts = data["concepts"]
    relations = data["relations"]    

    if request.method == 'POST':
        # Retrieve the lists of concepts and relations and convert them to the format supported by the app.
        # Request-- concepts: "a,b,c"  -> Concepts  (str): "a,b,c"
        concepts = ', '.join(list(OrderedDict.fromkeys([ s.strip() for s in request.form["concepts"].split(',') ])))
        relations = ', '.join(list(OrderedDict.fromkeys([ s.strip() for s in request.form["relations"].split(',') ])))

        # Build the JSON of the current concept map.
        data.update({
            "concepts": concepts,
            "relations": relations})

        adaptor.save_data(app_id, data)
        flash("Concept map saved successfully", "success")

    return render_template("conceptmapper/edit.html", app_id = app_id, concepts = data["concepts"], relations = data["relations"])


# Auxiliar routes
@adaptor.route("/export/<app_id>/")
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

    return render_template("conceptmapper/conceptmapper.html", app_id = app_id)

@adaptor.route("/export/<app_id>/app.xml")
def conceptmapper_widget(app_id):
    """
    conceptmapper_widget(app_id)
    This function points to the concept map instance.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.
    @return: The opensocial gadget of a concept map.
    """

    # In the templates, conceptmapper.html points to {{ url_for('adapt.conceptmapper_domain', app_id = app_id) }}
    # instead of domain.js (In the original app, the "concepts" variable was stored into the index.html file)
    # The domain name is not generated here.

    return render_template("conceptmapper/widget.xml", app_id = app_id)


@adaptor.route("/export/<app_id>/domain.js")
def conceptmapper_domain(app_id):
    """
    conceptmapper_domain(app_id)
    This function points to the javascript file associated to an instance of the concept map.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.
    @return: The javascript file with all its contents filled. Those contents are stored in the database.
    """

    #domain_orig = ["mass", "fluid", "density", "volume", "weight", "immersed object", "pressure", "force", "gravity", "acceleration", "Archimedes", "displacement", "equilibrium"]

    data = adaptor.load_data(app_id)

    debug = json.dumps(data["debug"])
    actionlogging = json.dumps(data["actionlogging"])
    show_prompts = json.dumps(data["show_prompts"])
    textarea_concepts = json.dumps(data["textarea_concepts"])
    combobox_concepts = json.dumps(data["combobox_concepts"])
    drop_external = json.dumps(data["drop_external"])

    concepts = json.dumps([ s.strip() for s in data["concepts"].split(',') ])
    relations = json.dumps([ s.strip() for s in data["relations"].split(',') ])

    return render_template("conceptmapper/domain.js", debug = debug, actionlogging = actionlogging, show_prompts = show_prompts,
                                            textarea_concepts = textarea_concepts, combobox_concepts = combobox_concepts, drop_external = drop_external,
                                            concepts = concepts, relations = relations)


@adaptor.route("/config/<app_id>", methods = ['GET'])
def load_configuration(app_id):
    """
    load_configuration(app_id)
    This function provides the configuration of a concept map.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.
    @return: The JSON response with the current values stored in the configuration (concepts, relations)
    """

    # This block contains analogous checks implemented for the def wrapper(appid) method in the AdaptorPlugin class.
    # Responses are JSON-encoded data.
    if not app_id:
        error_message = {
            'status': 400,
            'message': 'App id not provided: ' + request.url,
        }
        response = make_response(json.dumps(error_message, indent=True))
        response.mimetype = "application/json" 
        response.status_code = 400
        return response

    app = appstorage.get_app(app_id)
    if app is None:
        error_message = {
            'status': 404,
            'message': 'Concept map not found: ' + request.url,
        }
        response = make_response(json.dumps(error_message, indent=True))
        response.mimetype = "application/json"        
        response.status_code = 404
        return response

    data = adaptor.load_data(app_id)
    if data['adaptor_type'] != 'concept_mapper':
        error_message = {
            'status': 500,
            'message': 'This is not a Concept Map: ' + request.url,
        }
        response = make_response(json.dumps(error_message, indent=True))
        response.mimetype = "application/json" 
        response.status_code = 500
        return response
    else:
        data = adaptor.load_data(app_id)

        debug = data["debug"]
        actionlogging = data["actionlogging"]
        show_prompts = data["show_prompts"]
        textarea_concepts = data["textarea_concepts"]
        combobox_concepts = data["combobox_concepts"]
        drop_external = data["drop_external"]
        concepts = data["concepts"]
        relations = data["relations"]
        
        config_output = {'debug': debug, 'actionlogging': actionlogging, 'show_prompts': show_prompts,
                                    'textarea_concepts': textarea_concepts, 'combobox_concepts': combobox_concepts, 'drop_external': drop_external,
                                    'concepts': [concepts], 'relations': [relations]}

        response = make_response(json.dumps(config_output, indent=True))
        response.mimetype = "application/json"        
        return response


@adaptor.route("/config", methods = ['PUT', 'POST'])
def update_configuration(app_id):
    """
    update_configuration(app_id)
    This function stores new values in the configuration of a existing concept map.

    @param app_id: Identifier of the application. It will be unique within the list of user's apps.
    @param space_id: Identifier of the space. It will be used to verify the owner.    
    @return: The JSON response with the new configuration (concepts, relations)
    """
    if not request.json or not 'app_id' in request.json:
        abort(400)
    # Update the JSON config of the selected concept map.
    #What is recommended for testing? request.json vs request.get_json
    debug = request.json['debug']
    actionlogging = request.json['actionlogging']
    show_prompts = request.json['show_prompts']
    textarea_concepts = request.json['textarea_concepts']
    combobox_concepts = request.json['combobox_concepts']
    drop_external = request.json['drop_external']    
    concepts = request.json['concepts']
    relations = request.json['relations']
    
    data.update({
        "concepts": concepts,
        "relations": relations
    })
    adaptor.save_data(app_id, data)
    
    config_output = {'debug': debug, 'actionlogging': actionlogging, 'show_prompts': show_prompts, 'textarea_concepts': textarea_concepts,
                                'combobox_concepts':combobox_concepts, 'drop_external':drop_external, 'concepts' : [concepts], 'relations': [relations]}

    response = make_response(json.dumps(config_output, indent=True))
    response.mimetype = "application/json"
    #TODO: CORS variable in the AppComposer general configuration with a list of domains
    #response.headers['Access-Control-Allow-Origin'] = 'http://graasp.epfl.ch'
    
    return response #201 status?

"""
#Wrapper fucntions for CORS
# Usage: Specify origin and headers with @crossdomain(origin='http://localhost',headers='authorization')

from datetime import timedelta
from functools import update_wrapper
 
def crossdomain(origin=None, methods=None, headers=None,
                            max_age=21600, attach_to_all=True, automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()
 
    def get_methods():
        if methods is not None:
            return methods
 
        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']
 
def decorator(f):
    def wrapped_function(*args, **kwargs):
        if automatic_options and request.method == 'OPTIONS':
            resp = current_app.make_default_options_response()
        else:
            resp = make_response(f(*args, **kwargs))
        if not attach_to_all and request.method != 'OPTIONS':
            return resp
        h = resp.headers
        h['Access-Control-Allow-Origin'] = origin
        h['Access-Control-Allow-Methods'] = get_methods()
        h['Access-Control-Max-Age'] = str(max_age)
        if headers is not None:
            h['Access-Control-Allow-Headers'] = headers
        return resp
 
    f.provide_automatic_options = False
    f.required_methods = ['OPTIONS']
    return update_wrapper(wrapped_function, f)
return decorator
"""
