from flask import request, json, render_template, flash
from appcomposer.appstorage import remove_var
from appcomposer.appstorage.api import get_app, update_app_data
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import BundleManager, Bundle
from appcomposer.composers.translate.db_helpers import _db_get_owner_app, _db_get_proposals
from appcomposer.models import AppVar


@translate_blueprint.route("/proposed_list", methods=["POST", "GET"])
def translate_proposed_list():
    """
    Displays the list of proposed translations.
    """

    # No matter if we are handling a GET or POST, we require these parameters.
    appid = request.values["appid"]
    app = get_app(appid)

    appdata = json.loads(app.data)

    # Ensure that only the app owner can carry out these operations.
    owner_app = _db_get_owner_app(appdata["spec"])
    if app != owner_app:
        return render_template("composers/errors.html",
                               message="Not Authorized: You don't seem to be the owner of this app")

    # Get the list of proposed translations.
    proposal_vars = _db_get_proposals(app)
    proposed_translations = []
    for prop in proposal_vars:
        propdata = json.loads(prop.value)
        propdata["id"] = str(prop.var_id)
        proposed_translations.append(propdata)

    # If we received a POST with acceptButton set then we will need to merge the
    # proposal.
    if request.method == "POST" and request.values.get("acceptButton") is not None:
        proposal_id = request.values.get("proposals")
        if proposal_id is None:
            return render_template("composers/errors.html", message="Proposal not selected")

        merge_data = request.values.get("data")
        if merge_data is None:
            return render_template("composers/errors.html", message="Merge data was not provided")
        merge_data = json.loads(merge_data)

        # TODO: Optimize this. We already have the vars.
        proposal = AppVar.query.filter_by(app=app, var_id=proposal_id).first()
        if proposal is None:
            return render_template("composers/errors.html", message="Proposals not found")

        data = json.loads(proposal.value)
        bundle_code = data["bundle_code"]

        proposed_bundle = Bundle.from_messages(merge_data, bundle_code)

        bm = BundleManager.create_from_existing_app(app.data)
        bm.merge_bundle(bundle_code, proposed_bundle)

        update_app_data(app, bm.to_json())

        flash("Merge done.", "success")

        # Remove the proposal from the DB.
        remove_var(proposal)

        # Remove it from our current proposal list as well, so that it isn't displayed anymore.
        proposed_translations = [prop for prop in proposed_translations if prop["id"] != proposal_id]

    # The DENY button was pressed. We have to discard the whole proposal.
    elif request.method == "POST" and request.values.get("denyButton") is not None:
        proposal_id = request.values.get("proposals")
        if proposal_id is None:
            return render_template("composers/errors.html", message="Proposal not selected")

        proposal = AppVar.query.filter_by(app=app, var_id=proposal_id).first()
        if proposal is None:
            return render_template("composers/errors.html", message="Proposal not found")

        remove_var(proposal)

        # Remove it from our current proposal list as well, so that it isn't displayed anymore.
        proposed_translations = [prop for prop in proposed_translations if prop["id"] != proposal_id]

    return render_template("composers/translate/proposed_list.html", app=app, proposals=proposed_translations)