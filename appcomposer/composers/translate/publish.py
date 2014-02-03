from flask import request, render_template, url_for
from appcomposer.composers.translate import translate_blueprint

__author__ = 'lrg'


@translate_blueprint.route("/publish")
def translate_publish():
    """
    Show in a somewhat pretty way a link to an XML for a specific translation.
    """
    appid = request.values.get("appid")
    if appid is None:
        return render_template("composers/errors.html", message="appid not provided"), 500

    group = request.values.get("group")
    if group is None:
        return render_template("composers/errors.html", message="group not provided"), 500

    link = url_for('.app_xml', appid=appid, group=group, _external=True)

    return render_template("composers/translate/publish.html", link=link)