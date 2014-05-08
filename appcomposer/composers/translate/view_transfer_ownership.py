from flask import render_template
from appcomposer.composers.translate import translate_blueprint


@translate_blueprint.route("/transfer_ownership", methods=["GET", "POST"])
def transfer_ownership():
    return render_template("composers/translate/transfer_ownership.html")