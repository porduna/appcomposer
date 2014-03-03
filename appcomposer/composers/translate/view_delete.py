from flask import request, flash, redirect, url_for, render_template, json
from appcomposer.appstorage.api import get_app, delete_app
from appcomposer.babel import gettext
from appcomposer.composers.translate import translate_blueprint


@translate_blueprint.route("/delete", methods=["GET", "POST"])
def translate_delete():

    # If GET we display the confirmation screen and do not actually delete it.
    if request.method == "GET":
        appid = request.args.get("appid")
        if not appid:
            return "appid not provided", 400
        app = get_app(appid)
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
        app = get_app(appid)
        if app is None:
            return "App not found", 500

        delete_app(app)

        flash(gettext("App successfully deleted."), "success")

        return redirect(url_for("user.apps.index"))

