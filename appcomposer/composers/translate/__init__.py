from flask import Blueprint

from appcomposer.babel import lazy_gettext
from forms import UrlForm


info = {
    'blueprint': 'translate',
    'url': '/composers/translate',

    'new_endpoint': 'translate.translate_index',
    'edit_endpoint': 'translate.translate_selectlang',
    'delete_endpoint': 'translate.translate_delete',

    'name': lazy_gettext('Translate Composer'),
    'description': lazy_gettext('Translate an existing app.')
}

translate_blueprint = Blueprint(info['blueprint'], __name__)

# Maximum number of Apps that can have the same name.
# Note that strictly speaking the name is never the same.
# Repeated Apps have a (#number) appended to their name.
CFG_SAME_NAME_LIMIT = 30


# These imports NEED to be after the translate_blueprint assignment due to
# importing and cyclic dependencies issues.
import view_editlang
import view_selectlang
import view_proposed_list
import view_publish
import view_index
import view_delete
import view_others
import ajax
import api_publish
