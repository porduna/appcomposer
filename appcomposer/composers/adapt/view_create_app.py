from flask import url_for, flash, render_template, request, json, redirect
from appcomposer.appstorage import api as appstorage, api
from appcomposer.composers.adapt import adapt_blueprint, ADAPTORS
from appcomposer.csrf import verify_csrf
from appcomposer.login import requires_login



@adapt_blueprint.route("/create/<adaptor_type>/", methods=["GET", "POST"])
@requires_login
def adapt_create(adaptor_type):
    """
    adapt_create()
    Loads the form for creating new adaptor apps and the list of adaptor apps from a specific type.
    @return: The app unique id.
    """
    def build_edit_link(app):
        return url_for("adapt.adapt_edit", appid=app.unique_id)


    if adaptor_type not in ADAPTORS:
        flash("Invalid adaptor type", "error")
        return render_template('composers/adapt/create.html', apps=[], adaptor_type = adaptor_type, build_edit_link=build_edit_link)

    app_plugin = ADAPTORS[adaptor_type]

    apps = appstorage.get_my_apps(adaptor_type = adaptor_type)

    # If a get request is received, we just show the new app form and the list of adaptor apps
    if request.method == "GET":
        return render_template('composers/adapt/create.html', apps=apps, adaptor_type = adaptor_type, build_edit_link=build_edit_link)


    # If a post is received, we are creating an adaptor app.
    elif request.method == "POST":

        # Protect against CSRF attacks.
        if not verify_csrf(request):
            return render_template("composers/errors.html", message="Request does not seem to come from the right source (csrf check)"), 400

        # We read the app details provided by the user
        name = request.form["app_name"]
        app_description = request.form["app_description"]

        if not name:
            flash("An application name is required", "error")
            return render_template("composers/adapt/create.html", name=name, apps = apps, adaptor_type = adaptor_type, build_edit_link=build_edit_link)

        if not app_description:
            app_description = "No description"

        # Build the basic JSON schema of the adaptor app
        data = {
            'adaptor_version': '1',
            'name': unicode(name),
            'description': unicode(app_description),
            'adaptor_type': unicode(adaptor_type)
        }

        # Fill with the initial structure
        data.update(app_plugin['initial'])

        #Dump the contents of the previous block and check if an app with the same name exists.
        # (TODO): do we force different names even if the apps belong to another adaptor type?
        app_data = json.dumps(data)

        try:
            app = appstorage.create_app(name, 'adapt', app_data, description = app_description)
            appstorage.add_var(app, 'adaptor_type', unicode(adaptor_type))
        except appstorage.AppExistsException:
            flash("An App with that name already exists", "error")
            return render_template("composers/adapt/create.html", name=name, apps = apps, adaptor_type = adaptor_type, build_edit_link=build_edit_link)

        return redirect(url_for("adapt.adapt_edit", appid = app.unique_id))