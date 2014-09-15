from flask import request, render_template, url_for, flash, redirect
from appcomposer.composers.adapt import adapt_blueprint, ADAPTORS
from appcomposer.csrf import verify_csrf
from appcomposer.login import requires_login


@adapt_blueprint.route("/", methods=["GET", "POST"])
@requires_login
def adapt_appsearch():
    """
    adapt_appsearch
    Lets the user choose the App to adapt.
    """

    return render_template("composers/adapt/appsearch.html", adaptors=ADAPTORS)