from flask import Blueprint
from appcomposer.babel import lazy_gettext

info = {
    'blueprint': 'translate2',
    'url': '/composers/translate2',

    'new_endpoint': 'translate2.index',
    'edit_endpoint': 'translate2.index',
    'delete_endpoint': 'translate2.index',

    'name': lazy_gettext('Translate2 Composer'),
    'description': lazy_gettext('Translate an existing app.')
}

translate2_blueprint = Blueprint(info['blueprint'], __name__)


import view_main