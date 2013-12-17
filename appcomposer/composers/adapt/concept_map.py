import json
from collections import OrderedDict
from flask import render_template, request, flash
import appcomposer.appstorage.api as appstorage

from appcomposer.composers.adapt import adapt_blueprint

def concept_map_load(app, app_id, name, data):
    # If the app data is empty (basic JSON schema), we are editing a new app. Otherwise, the data values are loaded from the database.
    if len(data) == 4:
        return render_template("composers/adapt/conceptmapper/edit.html", app=app, app_id = app_id, name = name, n_rows = 0)

    concepts = data["concepts"]
    return render_template("composers/adapt/conceptmapper/edit.html", app=app, app_id = app_id, name = name, concepts = concepts)

def concept_map_edit(app, app_id, name, data):
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
    data.update({
        "concepts": concepts})

    appstorage.update_app_data(app, data)
    flash("Concept map saved successfully", "success")
    # flash(data["concepts"], "success")

    return render_template("composers/adapt/conceptmapper/edit.html", app=app, app_id = app_id, concepts = data["concepts"])


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

    app = appstorage.get_app(app_id)

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
   'initial' : lambda : {
        'concepts' : list()
   },
   'load' : concept_map_load,
   'edit' : concept_map_edit,
   'name' : 'Concept Mapper',
   'id' : 'concept_map',
}
