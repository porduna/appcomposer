from collections import defaultdict
import babel
from flask import request, flash, redirect, url_for, render_template, json
from appcomposer.appstorage import create_app, set_var
from appcomposer.appstorage.api import update_app_data, get_app
from appcomposer.composers.translate import translate_blueprint, backend
from appcomposer.composers.translate.bundles import BundleManager, InvalidXMLFileException
from appcomposer.composers.translate.helpers import _db_get_proposals, _find_unique_name_for_app, _db_get_owner_app


@translate_blueprint.route("/selectlang", methods=["GET", "POST"])
def translate_selectlang():
    """ Source language & target language selection."""

    # Note: The name pcode refers to the fact that the codes we deal with here are partial (do not include
    # the group).

    # We will build a list of possible languages using the babel library.
    languages = babel.core.Locale("en", "US").languages.items()
    languages.sort(key=lambda it: it[1])
    # TODO: Currently, we filter languages which contain "_" in their code so as to simplify.
    # Because we use _ throughout the composer as a separator character, trouble is caused otherwise.
    # Eventually we should consider whether we need to support special languages with _
    # on its code.
    targetlangs_codes = [lang[0] + "_ALL" for lang in languages if "_" not in lang[0]]

    targetlangs_list = [{"pcode": code, "repr": BundleManager.get_locale_english_name(
        *BundleManager.get_locale_info_from_code(code))} for code in targetlangs_codes]

    full_groups_list = [("ALL", "ALL"), ("10-13", "Preadolescence (age 10-13)"), ("14-18", "Adolescence (age 14-18)")]

    # As of now (may change in the future) if it is a POST we are creating the app for the first time.
    # Hence, we will need to carry out a full spec retrieval.
    if request.method == "POST":
        # URL to the XML spec of the gadget.
        appurl = request.form.get("appurl")
        spec = appurl
        if appurl is None or len(appurl) == 0:
            flash("An application URL is required", "error")
            return redirect(url_for("translate.translate_index"))

        base_appname = request.values.get("appname")
        if base_appname is None:
            return render_template("composers/errors.html", message="An appname was not specified")

        # Generates a unique (for the current user) name for the App,
        # based on the base name that the user himself chose. Note that
        # this method can actually return None under certain conditions.
        appname = _find_unique_name_for_app(base_appname)
        if appname is None:
            return render_template("composers/errors.html",
                                   message="Too many Apps with the same name. Please, choose another.")

        # Create a fully new App. It will be automatically generated from a XML.
        try:
            bm = BundleManager.create_new_app(appurl)
        except InvalidXMLFileException:
            return render_template("composers/errors.html",
                                   message="Invalid XML in either the XML specification file or the XML translation bundles that it links to")

        spec = bm.get_gadget_spec()  # For later


        # Build JSON data
        js = bm.to_json()

        # Create a new App from the specified XML
        app = create_app(appname, "translate", js)

        # Register our appurl as the "spec" in an app-specific variable in the DB. This will let us search later, for
        # certain advanced features.
        set_var(app, "spec", appurl)

        # Locate the owner of the App
        ownerApp = _db_get_owner_app(appurl)

        # If there isn't already an owner, declare ourselves as the owner.
        if ownerApp is None:
            set_var(app, "ownership", "")
        else:
            bm.merge_json(ownerApp.data)
            update_app_data(app, bm.to_json())
            flash("You are not the owner of this App, so the owner's translations have been merged", "success")

        # Find out which locales does the app provide (for now).
        translated_langs = bm.get_locales_list()

    # This was a GET, the app should exist already somehow, we will try to retrieve it.
    elif request.method == "GET":

        appid = request.args.get("appid")
        if appid is None:
            flash("appid not received", "error")

            # An appid is required.
            return redirect(url_for("user.apps.index"))

        app = get_app(appid)

        # Load a BundleManager from the app data.
        bm = BundleManager.create_from_existing_app(app.data)

        spec = bm.get_gadget_spec()

        translated_langs = bm.get_locales_list()


    # The following is again common for both GET (view) and POST (edit).

    # Check ownership.
    ownerApp = _db_get_owner_app(spec)
    if ownerApp == app:
        is_owner = True
    else:
        is_owner = False

    owner = ownerApp.owner
    if not is_owner and owner is None:
        flash("Error: Owner is None", "error")

    proposal_num = 0
    if is_owner:
        # Just for the count of proposals
        proposal_num = len(_db_get_proposals(app))

    # Build a dictionary. For each source lang, a list of source groups.
    src_groups_dict = defaultdict(list)
    for loc in translated_langs:
        src_groups_dict[loc["pcode"]].append(loc["group"])

    locales_codes = [tlang["pcode"] for tlang in translated_langs]

    # Remove from the suggested targetlangs those langs which are already present on the bundle manager,
    # because those will be added to the targetlangs by default.
    suggested_target_langs = [elem for elem in targetlangs_list if elem["pcode"] not in locales_codes]

    # We pass some parameters as JSON strings because they are generated dynamically
    # through JavaScript in the template.
    return render_template("composers/translate/selectlang.html",
                           app=app, # Current app object.
                           suggested_target_langs=suggested_target_langs, # Suggested (not already translated) langs
                           source_groups_json=json.dumps(src_groups_dict), # Source groups in a JSON string
                           full_groups_json=json.dumps(full_groups_list), # (To find names etc)
                           target_groups=full_groups_list, # Target groups in a JSON string
                           translated_langs=translated_langs, # Already translated langs
                           is_owner=is_owner, # Whether the loaded app has the "Owner" status
                           owner=owner, # Reference to the Owner
                           proposal_num=proposal_num)  # Number of pending translation proposals