from flask import request, flash, redirect, url_for, render_template, json
from appcomposer.appstorage.api import get_app, delete_app, NotAuthorizedException
from appcomposer.babel import gettext
from appcomposer.composers.translate import translate_blueprint


@translate_blueprint.route("/delete", methods=["GET", "POST"])
def translate_delete():
    """
    Handles the translate app delete endpoint. Only the user who owns the App can delete it.
    This is ensured at the appstorage level. A 401 code is returned if an attempt to delete
    other user's App is made.
    """

    # If GET we display the confirmation screen and do not actually delete it.
    if request.method == "GET":
        appid = request.args.get("appid")
        if not appid:
            return "appid not provided", 400
        app = get_app(appid)
        if app is None:
            return "App not found", 404
        return render_template("composers/dummy/delete.html", app=app)

    # If POST we consider whether the user clicked Delete or Cancel in the confirmation screen.
    elif request.method == "POST":
        # If the user didn't click delete he probably clicked cancel.
        # We return to the Apps View page.
        if not "delete" in request.form:
            return redirect(url_for("user.apps.index"))

        try:
            appid = request.form.get("appid")
            if not appid:
                return "appid not provided (bad request)", 400  # Bad request.
            app = get_app(appid)
            if app is None:
                return "App not found", 404  # Not found.

            delete_app(app)

            flash(gettext("App successfully deleted."), "success")

        except NotAuthorizedException:
            return render_template("composers/errors.html", message="Not Authorized"), 401

        return redirect(url_for("user.apps.index"))

