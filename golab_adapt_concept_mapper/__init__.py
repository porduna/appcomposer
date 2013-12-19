import json
from collections import OrderedDict
from flask import render_template, request, flash, url_for

from appcomposer.composers.adapt import create_adaptor
adaptor = create_adaptor('Concept Mapper', lambda : {
        'concepts' : ''
   })


@adaptor.edit_route
def edit(app_id):
    data = adaptor.load_data(app_id)
    name = data["concepts"]

    if request.method == 'GET':
        concepts = data["concepts"]
        return render_template("conceptmapper/edit.html", app_id = app_id, name = name, concepts = concepts)

    else:
        # Retrieve the list of concepts and convert it to the format supported by the app.
        # Request-- concepts: "a,b,c"  -> Concepts  (str): "a,b,c"
        concepts = ', '.join(list(OrderedDict.fromkeys([ s.strip() for s in request.form["concepts"].split(',') ])))

        # Build the JSON of the current concept map.
        data.update({
            "concepts": concepts})

        adaptor.save_data(app_id, data)
        flash("Concept map saved successfully", "success")
        return render_template("conceptmapper/edit.html", app_id = app_id, concepts = data["concepts"])


# Auxiliar routes
@adaptor.route("/export/<app_id>/conceptmapper.html")
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
    @return: The webpage of a concept map.
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

    domain = json.dumps([ s.strip() for s in data["concepts"].split(',') ])

    return render_template("conceptmapper/domain.js", domain = domain)

