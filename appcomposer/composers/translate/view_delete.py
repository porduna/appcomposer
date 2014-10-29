from flask import request, flash, redirect, url_for, render_template

from appcomposer import db
from appcomposer.appstorage.api import get_app, delete_app, NotAuthorizedException
from appcomposer.babel import gettext
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.db_helpers import _db_get_app_ownerships, _db_get_spec_apps
from appcomposer.csrf import verify_csrf
from appcomposer.models import AppVar
from appcomposer.login import requires_login


@translate_blueprint.route("/delete", methods=["GET", "POST"])
@requires_login
def translate_delete():
    """
    Handles the translate app delete endpoint. Only the user who owns the App can delete it.
    This is ensured at the appstorage level. A 401 code is returned if an attempt to delete
    other user's App is made.
    """

    appid = request.values.get("appid")
    if not appid:
        return "appid not provided", 400
    app = get_app(appid)
    if app is None:
        return "App not found", 404

    # Get our spec.
    spec = db.session.query(AppVar.value).filter_by(app=app, name="spec").first()[0]

    # Find out which languages we own.
    ownerships = _db_get_app_ownerships(app)

    # Find out which apps we can transfer to.
    transfer_apps = _db_get_spec_apps(spec)
    transfer_apps = [a for a in transfer_apps if a != app]

    # If GET we display the confirmation screen and do not actually delete it.
    if request.method == "GET":
        return render_template("composers/translate/delete.html", app=app, ownerships=ownerships,
                               transfer_apps=transfer_apps)

    # If POST we consider whether the user clicked Delete or Cancel in the confirmation screen.
    elif request.method == "POST":

        # Protect against CSRF attacks.
        if not verify_csrf(request):
            return render_template("composers/errors.html",
                                   message=gettext("Request does not seem to come from the right source (csrf check)")), 400

        # If the user didn't click delete he probably clicked cancel.
        # We return to the Apps View page.
        if not "delete" in request.form:
            return redirect(url_for("user.apps.index"))

        try:

            # If we have ownerships and we have someone to transfer them to,
            # then we need to do it.
            if len(ownerships) > 0 and len(transfer_apps) > 0:
                transfer_app_id = request.values.get("transfer")
                if transfer_app_id is None:
                    return render_template("composers/errors.html", message=gettext("transfer parameter missing")), 400
                transfer_app = get_app(transfer_app_id)
                if transfer_app is None:
                    return render_template("composers/errors.html", message=gettext("could not retrieve app")), 400

                # Transfer all ownerships to the selected app.
                for o in ownerships:
                    o.app = transfer_app
                    db.session.add(o)
                db.session.commit()

                transfer_app = get_app(transfer_app_id)

            delete_app(app)

            flash(gettext("App successfully deleted."), "success")

        except NotAuthorizedException:
            return render_template("composers/errors.html", message=gettext("Not Authorized")), 401

        return redirect(url_for("user.apps.index"))

