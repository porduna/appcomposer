import os
import random
from flask import Blueprint, render_template, flash, redirect, session, url_for, request, g
from appcomposer.appstorage.api import create_app
from appcomposer.db import db_session
from sqlalchemy.orm import scoped_session, sessionmaker
from forms import UrlForm, LangselectForm


info = {
    'blueprint': 'translate',
    'url': '/composers/translate',

    'new_endpoint': 'translate.translate_selectlang',
    'edit_endpoint': 'translate.translate_selectlang',
    'delete_endpoint': 'dummy.delete',

    'name': 'Translate Composer',
    'description': 'Translate an existing app.'
}


translate_blueprint = Blueprint(info['blueprint'], __name__)



import backend
print "Importing backend"


@translate_blueprint.route('/', methods=['GET', 'POST'])
def translate_index():
    form = UrlForm(request.form)
    
    # If it is a POST request (steps 2 & step 3), then request.form['appvar'] will not be None
    # Otherwise we will simply load the index
    if form.validate_on_submit():
        appurl = form.get_appurl()
        flash("App loaded successfully.")
       #return redirect(request.args.get("next") or url_for("translate.translate_index"))
        return redirect(url_for("adapt.adapt_index"))
        
    # It was a GET request (just viewing).
    return render_template('composers/translate/index.html', form=form)



#----------------------------------------
# other pages 
#----------------------------------------

@translate_blueprint.route("/selectlang", methods=["GET", "POST"])
def translate_selectlang():
    """ Source language & target language selection."""

    if request.method == "POST":
        # URL to the XML spec of the gadget.
        appurl = request.form["appurl"]

        # Get all the existing bundles.
        bm = backend.BundleManager()
        bm.load_spec(appurl)

        # Build JSON data
        js = bm.to_json()

        # Generate a name for the app.
        # TODO: Eventually, this name should probably be given explicitly by the user.
        appname = os.path.basename(appurl) + "_%d" % random.randint(0, 9999)

        # Create a new App from the specified XML
        app = create_app(appname, "translate", js)

        return render_template("composers/translate/selectlang.html")

    return render_template("composers/translate/selectlang.html")

@translate_blueprint.route("/edit")
def translate_edit():
    """Text editor for the selected language."""
    return render_template("composers/translate/edit.html")

@translate_blueprint.route("/about")
def translate_about():
    """Information about the translator application."""
    return render_template("composers/translate/about.html")

@translate_blueprint.route('/wip', methods=['GET', 'POST'])
def translate_wip():
    """Work in progress..."""    
    return render_template("composers/translate/index_test.html")        
