from flask import request, redirect, url_for, json, render_template, flash
from appcomposer.appstorage.api import get_app, update_app_data
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import BundleManager
from appcomposer.models import AppVar


@translate_blueprint.route("/merge_existing", methods=["GET", "POST"])
def translate_merge_existing():
    """
    Provides the logic for one of the merging features. This merging method
    was implemented before the "proposals" system, which is superior.
    Should probably be adapted or removed in the future.
    """
    appid = request.values.get("appid")
    if appid is None:
        # An appid is required.
        return redirect(url_for("user.apps.index"))
    app = get_app(appid)

    # If we are just viewing, we haven't chosen yet.
    if request.method == "GET":

        # Find out which is the XML of our app.
        data = json.loads(app.data)
        spec = data["spec"]

        # Find the Apps in the DB that match our criteria. We will need direct access to the DB, at least for now.
        appvars = AppVar.query.filter_by(name="spec", value=spec).all()
        apps_list = [var.app for var in appvars if var.app.composer == "translate"]

        return render_template('composers/translate/merge_existing.html', app=app, apps_list=apps_list)

    # It is a POST. The user has just chosen an app to merge, and we should hence carry out that merge.
    elif request.method == "POST":

        # Get the App to merge from the DB
        srcapp_id = request.values.get("srcapp")
        if srcapp_id is None:
            # The srcapp is required.
            return redirect(url_for("user.apps.index"))
        srcapp = get_app(srcapp_id)

        # Load our own app
        bm = BundleManager.create_from_existing_app(app.data)

        # Merge the srcapp into our's.
        bm.merge_json(srcapp.data)

        # Update the App's data.
        update_app_data(app, bm.to_json())

        flash("Translations merged", "success")

        # Redirect so that the App is reloaded with our changes applied.
        return redirect(url_for("translate.translate_selectlang", appid=appid))