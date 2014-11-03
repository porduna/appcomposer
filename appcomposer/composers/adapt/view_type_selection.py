from flask import flash, redirect, render_template, request, url_for

from appcomposer.babel import gettext
from appcomposer.composers.adapt import adapt_blueprint, ADAPTORS
from appcomposer.composers.translate.db_helpers import _db_get_spec_apps
from appcomposer.csrf import verify_csrf
from appcomposer.login import requires_login


@adapt_blueprint.route("/type_selection", methods=["GET", "POST"])
@requires_login
def adapt_type_selection():
    """
    adapt_type_selection()
    Loads the page that lets the user choose the adaptation type, and that lets the user view or duplicate
    an existing adaptation instead.
    """

    # We require the appurl parameter.
    appurl = request.values.get("appurl")
    if appurl is None:
        return render_template("composers/errors.html", message=gettext("appurl parameter not specified"))

    # Obtain a list of every adaptation that exists in the database for the specified appurl.
    # TODO: Move db_helpers somewhere else. Makes no sense to use translator files in the adaptor.
    apps_list = _db_get_spec_apps(appurl)
    apps = []
    for app in apps_list:
        if app.composer != "adapt":
            continue
        apps.append({
            "name": app.name,
            "desc": app.description,
            "owner": app.owner.name,
            "type": "adapt",  # TO-DO: Specify the specific adaptor sub-type.
            "app_id": app.unique_id
        })

    if request.method == "POST":

        # Protect against CSRF attacks.
        if not verify_csrf(request):
            return render_template("composers/errors.html",
                                   message="Request does not seem to come from the right source (csrf check)"), 400

        adaptor_type = request.form["adaptor_type"]

        if adaptor_type and adaptor_type in ADAPTORS:
            # In order to show the list of apps we redirect to other url
            return redirect(url_for("adapt.adapt_create", adaptor_type=adaptor_type))
        else:
            # An adaptor_type is required.
            flash("Invalid adaptor type", "error")
    return render_template("composers/adapt/type.html", adaptors=ADAPTORS, apps=apps)