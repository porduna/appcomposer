from flask import render_template, request

from appcomposer.composers.adapt import create_adaptor

adaptor = create_adaptor('Simple text', 
                initial = {'simple_text' : 'No text'})

@adaptor.edit_route
def edit(app_id):
    # Load data from the database for this application
    data = adaptor.load_data(app_id)

    # If data does not have 'simple_text', add the default value.
    if 'simple_text' not in data:
        data['simple_text'] = 'No text'

    if request.method == 'POST':
        value = request.form['simple_text']
        data['simple_text'] = value
        # Store it in the database
        adaptor.save_data(app_id, data)
    
    return render_template("simpletext/edit.html",  
                                value = data['simple_text'],
                                app_id = app_id)

@adaptor.route('/export/<app_id>/app.xml')
def app_xml(app_id):
    data = adaptor.load_data(app_id)
    return render_template("simpletext/app.xml", 
                                value = data['simple_text'])

@adaptor.route('/export/<app_id>/index.html')
def index_html(app_id):
    data = adaptor.load_data(app_id)
    return render_template("simpletext/simpletext.html",
                                value = data['simple_text'])

