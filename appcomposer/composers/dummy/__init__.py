from flask import Blueprint, render_template, request, url_for, redirect, json
from appcomposer.login import current_user
import appcomposer.appstorage.appstorage as appstorage
from appcomposer.models import App


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


@dummy_blueprint.route("/edit", methods=["GET", "POST"])
def edit():
    if request.method == "GET":
        appid = request.args.get("appid")
        if not appid:
            return "appid not provided", 400
        app = appstorage.get_app(appid)
        if app is None:
            return "App not found", 500

        # Load the dummy-specific data.
        # TODO: This.

        return render_template("composers/dummy/edit.html", app=app, text="not yet implemented")
    elif request.method == "POST":
        appid = request.form["appid"]
        text = request.form["text"]

        # Retrieve the app we're editing by its id.
        app = appstorage.get_app(appid)

        # Build our dummy composer JSON.
        data = {
            "dummy_version": 1,
            "text": text}
        datajson = json.dumps(data)

        # Modify the app
        app.data = datajson

        # Save the app with the modifications we have done
        appstorage.save_app(app)

        # TODO: Print a success message etc etc.

        return render_template("composers/dummy/edit.html", app=app, text=text)


@dummy_blueprint.route("/new", methods=["GET", "POST"])
def new():
    # If we receive a get we just want to show the page.
    if request.method == "GET":
        return render_template("composers/dummy/new.html")
    # If we receive a post we have filled the page and are creating the app.
    elif request.method == "POST":
        name = request.form["name"]
        user = current_user()
        app = appstorage.create_app(name, user, "dummy", data="{}")
        # TODO: Improve error handling. Display a tidy bootstrap message etc etc.
        return redirect(url_for("dummy.edit", appid=app.unique_id))



