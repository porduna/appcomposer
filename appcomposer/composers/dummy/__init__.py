from flask import Blueprint, render_template, request, url_for, redirect, json, flash
import appcomposer.appstorage.api as appstorage


info = {
    'blueprint': 'dummy',
    'url': '/composers/dummy',
    'new_endpoint': 'dummy.new',
    'edit_endpoint': 'dummy.edit',
    'delete_endpoint': 'dummy.delete',

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

        data = json.loads(app.data)
        text = data["text"]

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

        appstorage.update_app_data(app, data)

        flash("Saved successfully")

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
        app = appstorage.create_app(name, "dummy", data="{}")
        # TODO: Improve error handling. Display a tidy bootstrap message etc etc.
        return redirect(url_for("dummy.edit", appid=app.unique_id))



