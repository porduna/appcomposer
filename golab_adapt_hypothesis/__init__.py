import json
from flask import render_template, request, flash

from appcomposer.composers.adapt import create_adaptor

adaptor = create_adaptor('Hypothesis', initial = {
    'conditionals' : [
                {'text': 'IF','type': 'conditional'},
                {'text': 'THEN','type': 'conditional'},
                {'text': 'is equal to','type': 'conditional'},
        ],
    'inputs' : [],
    'outputs' : [],
   })


@adaptor.edit_route
def edit(app_id):
    data = adaptor.load_data(app_id)
    name = data["name"]

    if request.method == 'GET':
        conditionals_stored = data["conditionals"]
        inputs_stored = data["inputs"]
        outputs_stored = data["outputs"]

        # Format to load: inputs = [ {'text': 'immersed object','type': 'input'}, {'text': 'pressure','type': 'input'},... ]
        def load_hypothesis_list(list_stored):
            return ', '.join([ item['text'] for item in list_stored])

        conditionals = load_hypothesis_list(conditionals_stored)
        inputs = load_hypothesis_list(inputs_stored)
        outputs = load_hypothesis_list(outputs_stored)

        return render_template("hypothesis/edit.html", app_id = app_id, name = name, conditionals = conditionals, inputs = inputs, outputs = outputs)
    else:
        # Database manipulation
        conditionals_orig = request.form["conditionals"].split(',')
        inputs_orig = request.form["inputs"].split(',')
        outputs_orig = request.form["outputs"].split(',')


        # Conversion of the form input values to the hypothesis tool format below:
        # Request-- input_name = "input_type", value =  "a,b,c"  -> Output format = [ {'text':'a', 'type': 'input_type'}, {'text':'b', 'type': 'input_type', ...} ]
        def build_hypothesis_list(list_orig, element_type):
            lst = []
            for item in list_orig:
                dic = { 'text': item, 'type': element_type}
                lst.append(dic)
            return lst


        # A reserved word showed up.
        no_reserved = 'inputs'
        reserved_element_type = no_reserved[0:-1]

        inputs = build_hypothesis_list(inputs_orig, reserved_element_type)
        outputs = build_hypothesis_list(outputs_orig, 'output')
        conditionals = build_hypothesis_list(conditionals_orig, 'conditional')

        # Build the JSON of the current hypothesis tool.
        data.update({
            "conditionals": conditionals,
            "inputs": inputs,
            "outputs": outputs})

        # Template values
        conditionals_values = ', '.join([ item['text'] for item in conditionals])
        inputs_values = ', '.join([ item['text'] for item in inputs])
        outputs_values = ', '.join([ item['text'] for item in outputs])

        adaptor.save_data(app_id, data)
        flash("Hypothesis saved successfully", "success")

        return render_template("hypothesis/edit.html", app_id = app_id, conditionals = conditionals_values, inputs = inputs_values, outputs = outputs_values)


#
# Auxiliar routes
#

@adaptor.route("/export/<app_id>/hypothesis/hypothesis.html")
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

    return render_template("hypothesis/hypothesis.html", app_id = app_id)

@adaptor.route("/export/<app_id>/hypothesis/app.xml")
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

    return render_template("hypothesis/widget.xml", app_id = app_id)


@adaptor.route("/export/<app_id>/hypothesis/domain.js")
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

    data = adaptor.load_data(app_id)
    conditionals = data["conditionals"]
    inputs = data["inputs"]
    outputs = data["outputs"]

    domain = json.dumps(conditionals + inputs + outputs)
    return render_template("hypothesis/domain.js", domain = domain)

