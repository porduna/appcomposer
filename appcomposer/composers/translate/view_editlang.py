#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
from appcomposer.composers.translate.operations import ops_highlevel
import exceptions

from flask import request, render_template, flash, json, url_for, redirect

from appcomposer import db
from appcomposer.appstorage.api import get_app, update_app_data, add_var
from appcomposer.babel import gettext
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import BundleManager, Bundle
from appcomposer.composers.translate.db_helpers import _db_get_lang_owner_app, _db_declare_ownership, \
    save_bundles_to_db, \
    load_appdata_from_db
from appcomposer.composers.translate.operations.ops_exceptions import AppNotFoundException, BundleNotFoundException
from appcomposer.composers.translate.updates_handling import on_leading_bundle_updated
from appcomposer.csrf import verify_csrf
from appcomposer.login import requires_login
from appcomposer.composers.translate import common


def handle_editlang_GET(app, src_bundle, target_bundle):
    """
    Handles the edit lang screen GET request. It displays the bundle
    editing form.

    LOGIC:
      - Load the full source Bundle.
      - Load the full target Bundle.
      - Render the Bundles.

    :param app: Reference to the app which contains the Bundle to edit.
    :param src_bundle: The source Bundle.
    :type src_bundle: bundles.Bundle
    :param target_bundle: The target Bundle.
    :type target_bundle: bundles.Bundle
    :return:
    """

    target_pcode = "%s_%s" % (target_bundle.lang, target_bundle.country)

    # Get the owner for this target language.
    owner_app = _db_get_lang_owner_app(app.spec.url, target_pcode)

    # If the language has no owner, we declare ourselves as owners.
    if owner_app is None:
        _db_declare_ownership(app, target_pcode)
        owner_app = app

    # We override the standard Ownership's system is_owner.
    # TODO: Verify that this doesn't break anything.
    is_owner = owner_app == app

    # Get the language names
    target_translation_name = target_bundle.get_readable_name()
    source_translation_name = src_bundle.get_readable_name()

    return render_template("composers/translate/edit.html", is_owner=is_owner, app=app, srcbundle=src_bundle,
                           targetbundle=target_bundle, spec=app.spec.url, target_translation_name=target_translation_name,
                           source_translation_name=source_translation_name)


def handle_editlang_POST(app, src_bundle, target_bundle):
    """
    Handles the POST request on the editlang screen. The POST request
    is a request to modify the contents of a bundle.

    :param app:
    :type app: appcomposer.models.App
    :param srclang:
    :param targetlang:
    :param srcgroup:
    :param targetgroup:
    :return:
    """

    # Retrieve the bundles for our lang. For this, we build the code from the info we have.
    srcbundle_code = "%s_%s_%s" % (src_bundle.lang, src_bundle.country, src_bundle.group)
    targetbundle_code = "%s_%s_%s" % (target_bundle.lang, target_bundle.country, target_bundle.group)
    target_pcode = "%s_%s" % (target_bundle.lang, target_bundle.country)
    src_pcode = "%s_%s" % (src_bundle.lang, src_bundle.country)

    # Get the owner for this target language.
    owner_app = _db_get_lang_owner_app(app.spec.url, target_pcode)

    # If the language has no owner, we declare ourselves as owners.
    if owner_app is None:
        _db_declare_ownership(app, target_pcode)
        owner_app = app

    # We override the standard Ownership's system is_owner.
    # TODO: Verify that this doesn't break anything.
    is_owner = owner_app == app

    # Get the language names
    target_translation_name = target_bundle.get_readable_name()
    source_translation_name = src_bundle.get_readable_name()

    # END-OF GET-SPECIFIC PART



    # Protect against CSRF attacks.
    if not verify_csrf(request):
        raise exceptions.InvalidCSRFException()

    # Retrieve a list of all the key-values to save. That is, the parameters which start with _message_.
    messages = [(k[len("_message_"):], v) for (k, v) in request.values.items() if k.startswith("_message_")]

    # Save all the messages we retrieved from the POST or GET params into the Bundle.
    for identifier, msg in messages:
        if len(msg) > 0:  # Avoid adding empty messages.
            target_bundle.add_msg(identifier, msg)

    # Now we need to save the changes into the database.
    ops_highlevel.save_bundle(app, target_bundle)

    flash(gettext("Changes have been saved."), "success")

    propose_to_owner = request.values.get("proposeToOwner")
    if propose_to_owner is not None and owner_app != app:

        # Normally we will add the proposal to the queue. However, sometimes the owner wants to auto-accept
        # all proposals. We check for this. If the autoaccept mode is enabled on the app, we do the merge
        # right here and now.
        full_app_data = load_appdata_from_db(owner_app)
        obm = BundleManager.create_from_existing_app(full_app_data)
        if obm.get_autoaccept():
            flash(gettext("Changes are being applied instantly because the owner has auto-accept enabled"))

            # Merge into the owner app.
            obm.merge_bundle(targetbundle_code, target_bundle)

            # Now we need to update the owner app's data. Because we aren't the owners, we can't use the appstorage
            # API directly.
            owner_app.data = obm.to_json()
            db.session.add(owner_app)
            db.session.commit()
            save_bundles_to_db(owner_app, obm)

            # [Context: We are not the leading Bundles, but our changes are merged directly into the leading Bundle]
            # We report the change to a "leading" bundle.
            on_leading_bundle_updated(app.spec.url, target_bundle)

        else:

            # We need to propose this Bundle to the owner.
            # Note: May be confusing: app.owner.login refers to the generic owner of the App, and not the owner
            # we are talking about in the specific Translate composer.
            proposal_data = {"from": app.owner.login, "timestamp": time.time(), "bundle_code": targetbundle_code,
                             "bundle_contents": target_bundle.to_jsonable()}

            proposal_json = json.dumps(proposal_data)

            # Link the proposal with the Owner app.
            add_var(owner_app, "proposal", proposal_json)

            flash(gettext("Changes have been proposed to the owner"))

    # If we are the owner app.
    if owner_app == app:
        # [Context: We are the leading Bundle]
        # We report the change.
        on_leading_bundle_updated(app.spec.url, target_bundle)

    # Check whether the user wants to exit or to continue editing.
    if "save_exit" in request.values:
        print "REDIRECTION"
        return redirect(url_for("user.apps.index"))

    return redirect(url_for("translate.translate_edit", appid=app.unique_id, srclang=src_pcode, srcgroup=src_bundle.group,
                            targetlang=target_pcode, targetgroup=target_bundle.group))


@translate_blueprint.route("/edit", methods=["GET", "POST"])
@requires_login
def translate_edit():
    """
    Translation editor for the selected language.

    @note: Returns error 400 if the source language or group don't exist.
    """
    try:

        appid = common.get_required_param("appid")
        srclang = common.get_required_param("srclang")
        targetlang = common.get_required_param("targetlang")
        srcgroup = common.get_required_param("srcgroup")
        targetgroup = common.get_required_param("targetgroup")

        # Retrieve the application we want to view or edit.
        app = get_app(appid)
        if app is None:
            raise AppNotFoundException()

        src_bundle = ops_highlevel.load_bundle(app, srclang, srcgroup, create_if_not_found=False)
        target_bundle = ops_highlevel.load_bundle(app, targetlang, targetgroup, create_if_not_found=True)

        # This is a GET request. We need to show the target and source bundles.
        if request.method == "GET":
            return handle_editlang_GET(app, src_bundle, target_bundle)

        # This is a POST request. We need to save the entries.
        else:
            return handle_editlang_POST(app, src_bundle, target_bundle)

    except BundleNotFoundException, ex:
        return render_template("composers/errors.html", message=ex.message), 400
    except exceptions.ParameterNotProvidedException, ex:
        return render_template("composers/errors.html", message=ex.message), 400
    except AppNotFoundException, ex:
        return render_template("composers/errors.html", message=ex.message), 404
