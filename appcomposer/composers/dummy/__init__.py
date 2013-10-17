from flask import Blueprint, render_template


info = {
    'blueprint': 'dummy',
    'url': '/composers/dummy',
    'new_endpoint': 'dummy.new',

    'name': 'Dummy Composer',
    'description': 'Pretend that you are composing an app. For testing purposes.'
}

dummy_blueprint = Blueprint(info['blueprint'], __name__)


@dummy_blueprint.route("/")
def dummy_index():
    return render_template("composers/dummy/index.html")


@dummy_blueprint.route("/edit")
def edit():
    return render_template("composers/dummy/edit.html")

@dummy_blueprint.route("/new")
def new():
    return render_template("composers/dummy/new.html")
