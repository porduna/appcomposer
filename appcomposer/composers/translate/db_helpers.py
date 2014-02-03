from appcomposer import db
from appcomposer.appstorage.api import get_app_by_name
from appcomposer.composers.translate import CFG_SAME_NAME_LIMIT
from appcomposer.models import AppVar, App


def _db_get_owner_app(spec):
    """
    Gets from the database the App that is considered the Owner for a given spec.
    @param spec: String to the App's original XML.
    @return: The owner for the App. None if no owner is found.
    """
    related_apps_ids = db.session.query(AppVar.app_id).filter_by(name="spec",
                                                                 value=spec).subquery()
    owner_app_id = db.session.query(AppVar.app_id).filter(AppVar.name == "ownership",
                                                          AppVar.app_id.in_(related_apps_ids)).first()

    if owner_app_id is None:
        return None

    owner_app = App.query.filter_by(id=owner_app_id[0]).first()
    return owner_app


def _find_unique_name_for_app(base_name):
    """
    Generates a unique (for the current user) name for the app, using a base name.
    Because two apps for the same user cannot have the same name, if the base_name that the user chose
    exists already then we append (#num) to it.

    @param base_name: Name to use as base. If it's not unique (for the user) then we will append the counter.
    @return: The generated name, guaranteed to be unique for the current user, or None, if it was not possible
    to obtain the unique name. The failure would most likely be that the limit of apps with the same name has
    been reached. This limit is specified through the CFG_SAME_NAME_LIMIT variable.
    """
    if base_name is None:
        return None

    if get_app_by_name(base_name) is None:
        return base_name
    else:
        app_name_counter = 1
        while True:
            # Just in case, enforce a limit.
            if app_name_counter > CFG_SAME_NAME_LIMIT:
                return None
            composed_app_name = "%s (%d)" % (base_name, app_name_counter)
            if get_app_by_name(composed_app_name) is not None:
                app_name_counter += 1
            else:
                # Success. We found a unique name.
                return composed_app_name


def _db_get_proposals(app):
    return AppVar.query.filter_by(name="proposal", app=app).all()