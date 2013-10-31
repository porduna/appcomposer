from flask import Blueprint, render_template, flash, redirect, session, url_for, request, g
from appcomposer.db import db_session
from sqlalchemy.orm import scoped_session, sessionmaker
from forms import UrlForm, LangselectForm

translate_blueprint = Blueprint('translate', __name__)


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

@translate_blueprint.route("/selectlang")
def translate_selectlang():
    """Source language & target anguage selection."""
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
