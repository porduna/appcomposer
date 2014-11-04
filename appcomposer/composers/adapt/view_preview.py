import json
from flask import url_for, render_template
from werkzeug.utils import redirect
from appcomposer.appstorage import api as appstorage
from appcomposer.babel import gettext
from appcomposer.composers.adapt import adapt_blueprint, ADAPTORS
from appcomposer.composers.adapt.utils import shindig_url
from appcomposer.login import requires_login, current_user


@adapt_blueprint.route("/preview/<appid>/", methods=['GET', 'POST'])
def adapt_preview(appid):
    """
    adapt_preview(appid)
    Previews an application. You can preview the app of any user.
    # TODO: Eventually the preview feature should probably be merged into view_edit, through a read-only mode.
    LOGIN IS OPTIONAL FOR THIS METHOD.
    @param appid: Appid of the app to preview.
    """
    if not appid:
        return render_template("composers/errors.html", message=gettext("appid not provided")), 400

    # Check whether we are logged in.
    logged_in = current_user() is not None

    # TODO: Improve this: do not load the whole thing. We just need the variables.
    app = appstorage.get_app(appid)
    if app is None:
        return render_template("composers/errors.html", message=gettext("app not found")), 500

    adaptor_types = [var for var in app.appvars if var.name == 'adaptor_type']
    if not adaptor_types:
        return render_template("composers/errors.html", message=gettext("Error: no attached adaptor_type variable")), 500
    adaptor_type = adaptor_types[0].value

    if adaptor_type not in ADAPTORS:
        return render_template("composers/errors.html", message=gettext("Error: adaptor %s not currently supported") % adaptor_type), 500

    adaptor_plugin = ADAPTORS[adaptor_type]['adaptor']


    # TODO: URLs seem to be dependent on adaptor type. This is meant to work with jsconfig at least.

    # Calculate the URL for the Preview iframe.
    app_url = url_for('%s.app_xml' % adaptor_type, app_id=appid, _external=True)
    preview_url = shindig_url("/gadgets/ifr?nocache=1&url=%s" % app_url)

    # Retrieve the URL from the appdata.
    appdata = json.loads(app.data)
    spec_url = appdata["url"]


    return render_template("composers/adapt/preview.html", logged_in=logged_in, app_id=appid, app_url=app_url, spec_url=spec_url, name=app.name, preview_url=preview_url)