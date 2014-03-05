from flask import render_template, request

from appcomposer.composers.adapt import create_adaptor

adaptor = create_adaptor('Custom Configuration',
                initial = {'config_value' : 'No text'})

@adaptor.edit_route
def edit(app_id):
    # Load data from the database for this application
    data = adaptor.load_data(app_id)

    if 'config_value' not in data:
        data['config_value'] = 'No text'

    if request.method == 'POST':
        value = request.form['config_value']
        data['config_value'] = value
        # Store it in the database
        adaptor.save_data(app_id, data)

    return render_template("custom_configuration/edit.html",
                                value = data['config_value'])
