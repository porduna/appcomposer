from flask import Blueprint, render_template, request, url_for, redirect, json, flash
import appcomposer.appstorage.api as appstorage
from appcomposer.babel import lazy_gettext, gettext

info = {
    'blueprint': 'dummy',
    'url': '/composers/dummy',
    'new_endpoint': 'dummy.new',
    'edit_endpoint': 'dummy.edit',
    'delete_endpoint': 'dummy.delete',

    'name': lazy_gettext('Dummy Composer'),
    'description': lazy_gettext('Pretend that you are composing an app. For testing purposes.')
}

dummy_blueprint = Blueprint(info['blueprint'], __name__)


@dummy_blueprint.route("/")
def dummy_index():
    return render_template("composers/dummy/index.html")


@dummy_blueprint.route("/delete", methods=["GET", "POST"])
def delete():

    # If GET we display the confirmation screen and do not actually delete it.
    if request.method == "GET":
        appid = request.args.get("appid")
        if not appid:
            return "appid not provided", 400
        app = appstorage.get_app(appid)
        if app is None:
            return "App not found", 500
        return render_template("composers/dummy/delete.html", app=app)

    # If POST we consider whether the user clicked Delete or Cancel in the confirmation screen.
    elif request.method == "POST":
        # If the user didn't click delete he probably clicked cancel.
        # We return to the Apps View page.
        if not "delete" in request.form:
            return redirect(url_for("user.apps.index"))

        appid = request.form.get("appid")
        if not appid:
            return "appid not provided", 400
        app = appstorage.get_app(appid)
        if app is None:
            return "App not found", 500

        appstorage.delete_app(app)

        flash(gettext("App successfully deleted."), "success")

        return redirect(url_for("user.apps.index"))


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

        return render_template("composers/dummy/edit.html", app=app, text=text)
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

        flash(gettext("Saved successfully"), "success")

        # TODO: Print a success message etc etc.

        # If the user clicked on saveexit we redirect to appview, otherwise
        # we stay here.
        if "saveexit" in request.form:
            return redirect(url_for("user.apps.index"))

        return render_template("composers/dummy/edit.html", app=app, text=text)


@dummy_blueprint.route("/new", methods=["GET", "POST"])
def new():
    # If we receive a get we just want to show the page.
    if request.method == "GET":
        return render_template("composers/dummy/new.html")
    # If we receive a post we have filled the page and are creating the app.
    elif request.method == "POST":
        name = request.form["name"]

        try:
            app = appstorage.create_app(name, "dummy", data='{"text":""}')
        except appstorage.AppExistsException:
            flash(gettext("An App with that name exists already"), "error")
            return render_template("composers/dummy/new.html", name=name)

        return redirect(url_for("dummy.edit", appid=app.unique_id))



