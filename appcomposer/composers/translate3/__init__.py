from flask import Blueprint, render_template, request, url_for, redirect, json, flash
import appcomposer.appstorage.api as appstorage
from appcomposer.babel import lazy_gettext, gettext

info = {
    'blueprint': 'translate3',
    'url': '/composers/translate3',
    'new_endpoint': 'translate3.new',
    'edit_endpoint': 'translate3.edit',
    'delete_endpoint': 'translate3.delete',

    'name': lazy_gettext('Translate 3 Composer'),
    'description': lazy_gettext('Translate 3 composer. Translate an app.')
}

translate3_blueprint = Blueprint(info['blueprint'], __name__)


# This import is a must.
import api


@translate3_blueprint.route("/")
def translate_index():
    return "Translate 3 index"


@translate3_blueprint.route("/delete", methods=["GET", "POST"])
def delete():
    return ""


@translate3_blueprint.route("/edit", methods=["GET", "POST"])
def edit():
    return ""


@translate3_blueprint.route("/new", methods=["GET", "POST"])
def new():
    return ""





