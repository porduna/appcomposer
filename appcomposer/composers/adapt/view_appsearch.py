from flask import request, render_template, url_for, flash, redirect
from appcomposer.composers.adapt import adapt_blueprint, ADAPTORS
from appcomposer.csrf import verify_csrf
from appcomposer.login import requires_login


@adapt_blueprint.route("/appsearch", methods=["GET", "POST"])
@requires_login
def adapt_appsearch():
    """
    adapt_appsearch
    Lets the user choose the App to adapt.
    """
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

    return render_template("composers/adapt/appsearch.html", adaptors=ADAPTORS)