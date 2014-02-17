from appcomposer import db
from appcomposer.appstorage.api import get_app_by_name, add_var
from appcomposer.composers.translate import CFG_SAME_NAME_LIMIT
from appcomposer.models import AppVar, App

"""
REMARKS ABOUT APPVARS FOR THE TRANSLATOR:

A lownership AppVar identifies that the owner of a Spec/Language combination. It is attached
to the App that owns it, and has "lownership" as its AppVar name, and the language code (ex:
ca_ES) as its value.

As of now, we use the term "lowner" rather than "owner" because the system is being redesigned and
major changes are required.
"""


def _db_get_ownerships(spec):
    """
    Gets every single lownership for a spec.
    @param spec: The spec whose lownerships to retrieve.
    @return: List of lownerships.
    """
    related_apps_ids = db.session.query(AppVar.app_id).filter_by(name="spec",
                                                                 value=spec).subquery()

    # Among those AppVars for our Spec, we try to locate a lownership AppVar.
    owner_apps = db.session.query(AppVar).filter(AppVar.name == "lownership",
                                                 AppVar.app_id.in_(related_apps_ids)).all()

    return owner_apps


def _db_get_lowner_app(spec, lang_code):
    """
    Gets from the database the App that is considered the Owner for a given spec and language.
    @param spec: String to the App's original XML.
    @param lang_code: The language code. It should actually be a partial, lang_territory code. Only the
    language without the territory is NOT enough.
    @return: The owner for the App and language. None if no owner is found.
    """
    related_apps_ids = db.session.query(AppVar.app_id).filter_by(name="spec",
                                                                 value=spec).subquery()

    # Among those AppVars for our Spec, we try to locate a lownership AppVar for our
    # lang code.
    owner_app_id = db.session.query(AppVar.app_id).filter(AppVar.name == "lownership",
                                                          AppVar.value == lang_code,
                                                          AppVar.app_id.in_(related_apps_ids)).first()

    if owner_app_id is None:
        return None

    owner_app = App.query.filter_by(id=owner_app_id[0]).first()
    return owner_app


def _db_declare_ownership(owner_app, lang_code):
    """
    Declares lownership over a given Spec and Langcode. The CALLER is responsible of ensuring
    that no other owner for that spec and lang code exists before invoking this method.

    @param owner_app: Owner App for the language.
    @param lang_code: Language code to own.
    @return: None.
    """
    add_var(owner_app, "lownership", lang_code)


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