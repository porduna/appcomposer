from flask import Blueprint, flash, json, redirect, render_template, request, url_for

import appcomposer.appstorage.api as appstorage

# Required imports for a customized app view for the adapt tool (a possible block to be refactored?)
from appcomposer.babel import lazy_gettext
from appcomposer.login import requires_login

info = {
    'blueprint': 'adapt',
    'url': '/composers/adapt',

    'new_endpoint': 'adapt.adapt_index',
    'edit_endpoint': 'adapt.adapt_edit',
    'create_endpoint': 'adapt.adapt_create',
    'delete_endpoint': 'dummy.delete',

    'name': lazy_gettext('Adaptor Composer'),
    'description': lazy_gettext('Adapt an existing app.')
}

adapt_blueprint = Blueprint(info['blueprint'], __name__)

ADAPTORS = {
    # 'identifier' : {
    #     'load' : function,
    #     'edit' : function,
    #     'name' : 'Something',
    # }
}

def register_plugin(plugin_data):
    for field in 'load', 'edit', 'id':
        if field not in plugin_data:
            raise Exception("Plug-in misconfigured. Field %s missing." % field)

    plugin_id = plugin_data['id']
    if plugin_id in ADAPTORS:
        raise Exception("Plug-in id already registered: %s" % plugin_id)

    ADAPTORS[plugin_id] = plugin_data


#
# Register the plug-ins. In the future we might have something more serious, relying on the
# extension system for flask.
#

from .concept_map import data as concept_map_data
register_plugin(concept_map_data)

from .hypothesis import data as hypothesis_data
register_plugin(hypothesis_data)

from .edt import data as edt_data
register_plugin(edt_data)

# 
# Common code 
# 


@adapt_blueprint.route("/", methods=["GET", "POST"])
@requires_login
def adapt_index():
    """
    adapt_index()
    Loads the main page with the selection of adaptor apps (concept map, hypothesis or experiment design).
    @return: The adaptor type that the user has selected.
    """
    if request.method == "POST":
        adaptor_type = request.form["adaptor_type"]

        if adaptor_type and adaptor_type in ADAPTORS:
            # In order to show the list of apps we redirect to other url
            return redirect(url_for("adapt.adapt_create", adaptor_type = adaptor_type))
        else:
            # An adaptor_type is required.
            flash("Invalid adaptor type", "error")

    return render_template("composers/adapt/index.html", adaptors = ADAPTORS)

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

    apps = appstorage.get_my_apps(adaptor_type = adaptor_type)

    # If a get request is received, we just show the new app form and the list of adaptor apps
    if request.method == "GET":
        return render_template('composers/adapt/create.html', apps=apps, adaptor_type = adaptor_type, build_edit_link=build_edit_link)


    # If a post is received, we are creating an adaptor app.
    elif request.method == "POST":

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

        #Dump the contents of the previous block and check if an app with the same name exists.
        # (TODO): do we force different names even if the apps belong to another adaptor type?
        app_data = json.dumps(data)

        try:
            app = appstorage.create_app(name, 'adapt', app_data)
            appstorage.add_var(app, 'adaptor_type', unicode(adaptor_type))
        except appstorage.AppExistsException:
            flash("An App with that name already exists", "error")
            return render_template("composers/adapt/create.html", name=name, apps = apps, adaptor_type = adaptor_type, build_edit_link=build_edit_link)

        return redirect(url_for("adapt.adapt_edit", appid = app.unique_id))


@adapt_blueprint.route("/edit/<appid>/", methods = ['GET', 'POST'])
@requires_login
def adapt_edit(appid):
    """
    adapt_edit()
    Form-based user interface for editing the contents of an adaptor app.
    @return: The final app with all its fields stored in the database.
    """
    if not appid:
        return "appid not provided", 400
    app = appstorage.get_app(appid)
    if app is None:
        return "App not found", 500

    data = json.loads(app.data)
    name = data["name"]
    adaptor_type = data["adaptor_type"]

    if adaptor_type not in ADAPTORS:
        return ":-("

    adaptor_plugin = ADAPTORS[adaptor_type]

    if request.method == "GET":
        return adaptor_plugin['load'](app, appid, name, data)

    else: # Only GET and POST in the route
        return adaptor_plugin['edit'](app, appid, name, data)

## Tests

@adapt_blueprint.route("/more/<uuid_test>/", methods = ['GET', 'POST'])
def adapt_uuid(uuid_test):
    return uuid_test

"""
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html'), 404
"""
