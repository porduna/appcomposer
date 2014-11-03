from flask import url_for, render_template
from werkzeug.utils import redirect
from appcomposer.appstorage import api as appstorage
from appcomposer.babel import gettext
from appcomposer.composers.adapt import adapt_blueprint, ADAPTORS
from appcomposer.login import requires_login


@adapt_blueprint.route("/edit/<appid>/", methods=['GET', 'POST'])
@requires_login
def adapt_edit(appid):
    """
    adapt_edit()
    Form-based user interface for editing the contents of an adaptor app.
    @return: The final app with all its fields stored in the database.
    """
    if not appid:
        return "appid not provided", 400

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

    return redirect(url_for(adaptor_plugin._edit_endpoint, appid=appid))