"""
Module for high-level translator operations.
"""
import json
from appcomposer.appstorage.api import get_app_by_name, create_app
from appcomposer.composers.translate import CFG_SAME_NAME_LIMIT
from appcomposer.composers.translate.bundles import BundleManager
from appcomposer.composers.translate.db_helpers import save_bundles_to_db, _db_get_lang_owner_app, _db_declare_ownership
from appcomposer.composers.translate.updates_handling import on_leading_bundle_updated


def find_unique_name_for_app(base_name):
    """
    Generates a unique (for the current user) name for the app, using a base name.
    Because two apps for the same user cannot have the same name, if the base_name that the user chose
    exists already then we append (#num) to it. The number starts at 1.

    :param base_name: Name to use as base. If it's not unique (for the user) then we will append the counter.
    :return: The generated name, guaranteed to be unique for the current user, or None, if it was not possible
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


def create_new_app(name, spec_url):
    """
    Creates a completely new application from the URL for a standard OpenSocial XML specification.
    This operation needs to request the external XML and in some cases external XMLs referred by it.
    As such, it can take a while ot complete, and there are potential security issues.

    :param name: Name to assign to the new Application. See find_unique_name_for_app.
    :type name: str
    :param spec_url: The URL to the OpenSocial XML specification file for the application.
    :type spec_url: str
    :return: (app, bm) tuple. App is the App DAO while bm is the BundleManager with the contents.
    :rtype: (App, BundleManager)
    """
    bm = BundleManager.create_new_app(spec_url)
    spec = bm.get_gadget_spec()

    # Build JSON data
    js = bm.to_json()
    # TODO: Remove this.
    # As an intermediate step towards db migration we remove the bundles from the app.data.
    # We cannot remove it from the bm to_json itself.
    jsdata = json.loads(js)
    if "bundles" in jsdata:
        del jsdata["bundles"]
    js = json.dumps(jsdata)

    # Create a new App from the specified XML
    app = create_app(name, "translate", spec_url, js)
    save_bundles_to_db(app, bm)

    # Handle Ownership-related logic here.
    # Locate the owner for the App's DEFAULT language.
    ownerApp = _db_get_lang_owner_app(spec_url, "all_ALL")
    # If there isn't already an owner for the default languages, we declare ourselves
    # as the owner for this App's default language.
    if ownerApp is None:
        _db_declare_ownership(app, "all_ALL")
        ownerApp = app

        # Report initial bundle creation. Needed for the MongoDB replica.
        for bundle in bm.get_bundles("all_ALL"):
            on_leading_bundle_updated(spec, bundle)

    # We do the same for the other included languages which are not owned already.
    # If the other languages have a translation but no owner, then we declare ourselves as their owner.
    for partialcode in bm.get_langs_list():
        otherOwner = _db_get_lang_owner_app(spec_url, partialcode)
        if otherOwner is None:
            _db_declare_ownership(app, partialcode)

            # Report initial bundle creation. Needed for the MongoDB replica.
            for bundle in bm.get_bundles(partialcode):
                on_leading_bundle_updated(spec, bundle)

    return app, bm





