from flask import Blueprint, flash, json, redirect, render_template, request, url_for
from appcomposer.composers.adapt import adapt_blueprint, ADAPTORS
from appcomposer.csrf import verify_csrf
from appcomposer.login import requires_login


@adapt_blueprint.route("/", methods=["GET", "POST"])
@requires_login
def adapt_index():
    """
    adapt_index()
    Loads the main page with the selection of adaptor apps (concept map, hypothesis or experiment design).
    @return: The adaptor type that the user has selected.
    """
    if request.method == "POST":

        # Protect against CSRF attacks.
        if not verify_csrf(request):
            return render_template("composers/errors.html",
                                   message="Request does not seem to come from the right source (csrf check)"), 400

        adaptor_type = request.form["adaptor_type"]

        if adaptor_type and adaptor_type in ADAPTORS:
            # In order to show the list of apps we redirect to other url
            return redirect(url_for("adapt.adapt_create", adaptor_type = adaptor_type))
        else:
            # An adaptor_type is required.
            flash("Invalid adaptor type", "error")
    return render_template("composers/adapt/index.html", adaptors = ADAPTORS)