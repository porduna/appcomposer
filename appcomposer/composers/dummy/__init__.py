from flask import Blueprint, render_template


info = {
        'blueprint' : 'dummy',
        'url' : '/composers/dummy',
        'new_endpoint' : 'translate.new'
        }


dummy_blueprint = Blueprint(info['blueprint'], __name__)

@dummy_blueprint.route("/")
def dummy_index():
    return render_template("composers/dummy/index.html")
