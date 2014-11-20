import json
from appcomposer import db
from appcomposer.appstorage.api import get_app_by_name, add_var
from appcomposer.composers.translate import CFG_SAME_NAME_LIMIT
from appcomposer.models import AppVar, App, Spec, Bundle, Message

"""
REMARKS ABOUT APPVARS FOR THE TRANSLATOR:

An ownership AppVar identifies that the owner of a Spec/Language combination. It is attached
to the App that owns it, and has "ownership" as its AppVar name, and the language code (ex:
ca_ES) as its value.
"""


def _db_get_diff_specs():
    """
    Gets a list of the different specs that are in the database.
    @return: List of different specs.
    """
    spec_values = db.session.query(Spec.url).distinct()
    specs = [val[0] for val in spec_values]
    return specs


def _db_get_ownerships(spec):
    """
    Gets every single ownership for a spec. It will only work on "translate" specs.
    @param spec: The spec whose ownerships to retrieve.
    @return: List of ownerships.
    """
    related_apps_ids = db.session.query(App.id).filter(App.spec.has(Spec.url == spec)).subquery()

    # Among those AppVars for our Spec, we try to locate an ownership AppVar.
    owner_apps = db.session.query(AppVar).filter(AppVar.name == "ownership",
                                                 AppVar.app_id.in_(related_apps_ids)).all()

    # Filter those that do not belong to the translator. This should probably be done directly in one of the previous
    # query, but we need to find out how. (First attempts have failed).
    owner_apps = [owner_app for owner_app in owner_apps if owner_app.app.composer == "translate"]

    return owner_apps


def _db_get_app_ownerships(app):
    """
    Gets every single ownership for an app.
    @param app: The app whose ownerships to retrieve.
    @return: List of ownerships.
    """
    ownerships = db.session.query(AppVar).filter_by(name="ownership",
                                                    app=app).all()
    return ownerships


def _db_get_spec_apps(spec_url):
    """
    Gets from the database the list of apps with the specified spec.
    @param spec_url: String to the App's original XML.
    @return: List of apps with the specified spec."
    """
    spec = db.session.query(Spec).filter_by(url=spec_url).first()
    if spec is None:
        return []
    else:
        return spec.apps


def _db_get_lang_owner_app(spec, lang_code):
    """
    Gets from the database the App that is considered the Owner for a given spec and language.
    @param spec: String to the App's original XML.
    @param lang_code: The language code. It should actually be a partial, lang_territory code. Only the
    language without the territory is NOT enough.
    @return: The owner for the App and language. None if no owner is found.
    """
    related_apps_ids = db.session.query(App.id).filter(App.spec.has(Spec.url == spec)).subquery()

    # TODO: Check whether we can optimize this code thanks to the spec_url update.

    # Among those AppVars for our Spec, we try to locate an ownership AppVar for our
    # lang code.
    owner_app_ids = db.session.query(AppVar.app_id).filter(AppVar.name == "ownership",
                                                           AppVar.value == lang_code,
                                                           AppVar.app_id.in_(related_apps_ids)).all()

    # TODO: We shouldnt repeat this.
    owner_appvars = db.session.query(AppVar).filter(AppVar.name == "ownership",
                                                    AppVar.value == lang_code,
                                                    AppVar.app_id.in_(related_apps_ids)).all()

    owner_app_id = [owner_appvar.app_id for owner_appvar in owner_appvars if owner_appvar.app.composer == "translate"]

    # TODO: Add some tests to make sure that we do not get confused if another composer uses the same appvar names.
    # TODO: Make this better. Right now it's somewhat kludgey.

    if owner_app_id is None or len(owner_app_id) == 0:
        return None

    owner_app = App.query.filter_by(id=owner_app_id[0]).first()
    return owner_app


def _db_declare_ownership(owner_app, lang_code):
    """
    Declares ownership over a given Spec and Langcode. The CALLER is responsible of ensuring
    that no other owner for that spec and lang code exists before invoking this method.

    @param owner_app: Owner App for the language.
    @param lang_code: Language code to own.
    @return: None.
    """
    add_var(owner_app, "ownership", lang_code)


def _db_transfer_ownership(lang, from_app, target_app):
    """
    Transfers ownership of a language from an app to another.
    """
    ownership = db.session.query(AppVar).filter(AppVar.app == from_app,
                                                AppVar.name == "ownership", AppVar.value == lang).first()
    if ownership is None:
        raise Exception("Could not find specified ownership")
    ownership.app = target_app
    db.session.add(ownership)
    db.session.commit()


def _find_unique_name_for_app(base_name):
    """
    Generates a unique (for the current user) name for the app, using a base name.
    Because two apps for the same user cannot have the same name, if the base_name that the user chose
    exists already then we append (#num) to it. The number starts at 1.

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


def save_bundles_to_db(app, bm):
    """
    Saves the translation data in the Bundle Manager to the DB.
    :param app: The App object to save to.
    :type app: App
    :param bm: BundleManager whose data to use.
    :type bm: BundleManager
    :return:

    TO-DO: Optimize this. It exists mostly because of the DB changes.
    """
    j = bm.to_json()

    data = json.loads(j)
    bundles = data["bundles"]
    for bundle_code, bundle in bundles.items():
        country, lang, group, messages = bundle["country"], bundle["lang"], bundle["group"], bundle["messages"]
        full_lang = "%s_%s" % (lang, country)

        # Create the bundle if we need to.
        bundleObj = db.session.query(Bundle).filter_by(lang=full_lang, target=group).first()
        if bundleObj is None:
            # We create a new bundle.
            bundleObj = Bundle(full_lang, group)
        bundleObj.app = app

        db.session.add(bundleObj)

        # Create each message if we need to.
        for key, value in bundle["messages"].items():
            messageObj = db.session.query(Message).filter_by(key=key).first()
            if messageObj is None:
                # We create a new message.
                messageObj = Message(key, value)
            messageObj.bundle = bundleObj
            messageObj.value = value

            db.session.add(messageObj)


        db.session.commit()

