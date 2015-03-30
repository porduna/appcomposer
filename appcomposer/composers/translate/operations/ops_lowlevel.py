"""
Contains the low-level operations which are not meant to be used from outside this module.
"""
from appcomposer.appstorage.api import update_app_data
from appcomposer.composers.translate.db_helpers import _db_get_ownerships, save_bundles_to_db


def do_languages_initial_merge(app, bm):
    """
    Carries out an initial merge. Bundles from the language-owners are merged into the
    app.
    @param app: Target app. App into which the bundles of each language owner are merged.
    @param bm: Target BundleManager. Bundle manager into which the bundles of each language owner are merged.
    @note: The App's data is updated automatically to reflect the new merge.
    """

    # Retrieve every single "owned" App for that xmlspec.
    ownerships = _db_get_ownerships(bm.get_gadget_spec())

    for ownership in ownerships:
        language = ownership.value
        ownerapp = ownership.app
        bm.merge_language(language, ownerapp)

    update_app_data(app, bm.to_json())
    save_bundles_to_db(app, bm)