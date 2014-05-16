import babel
import urllib2
import traceback
import xml.dom.minidom as minidom
from collections import defaultdict

from flask import request, flash, redirect, url_for, render_template, json
from requests.exceptions import MissingSchema
from appcomposer.composers.translate.updates_handling import on_leading_bundle_updated
from appcomposer.utils import get_original_url
from appcomposer.appstorage import create_app, set_var
from appcomposer.appstorage.api import update_app_data, get_app
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import BundleManager, InvalidXMLFileException
from appcomposer.composers.translate.db_helpers import _find_unique_name_for_app, _db_get_proposals, _db_get_lang_owner_app, _db_declare_ownership, _db_get_ownerships


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

        try:
            # XXX FIXME
            # TODO: this makes this method to call twice the app_xml. We shouldn't need
            # that. We should have the contents here downloaded for later.
            if appurl.startswith(('http://','https://')):
                print appurl
                xmldoc = minidom.parseString(urllib2.urlopen(appurl).read())
                appurl = get_original_url(xmldoc, appurl)
                print "New app xml:", appurl
        except:
            traceback.print_exc()
            pass

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
                                   message="Invalid XML in either the XML specification file or the XML translation bundles that it links to"), 400
        except MissingSchema:
            return render_template("composers/errors.html",
                                   message="Failed to retrieve the XML spec. The URL was maybe invalid."), 400

        spec = bm.get_gadget_spec()  # For later


        # Build JSON data
        js = bm.to_json()

        # Create a new App from the specified XML
        app = create_app(appname, "translate", js)

        # Register our appurl as the "spec" in an app-specific variable in the DB. This will let us search later, for
        # certain advanced features.
        set_var(app, "spec", appurl)


        # Handle Ownership-related logic here.
        # Locate the owner for the App's DEFAULT language.
        ownerApp = _db_get_lang_owner_app(appurl, "all_ALL")
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
            otherOwner = _db_get_lang_owner_app(appurl, partialcode)
            if otherOwner is None:
                _db_declare_ownership(app, partialcode)

                # Report initial bundle creation. Needed for the MongoDB replica.
                for bundle in bm.get_bundles(partialcode):
                    on_leading_bundle_updated(spec, bundle)

        # Advanced merge. Merge owner languages into our bundles.
        do_languages_initial_merge(app, bm)


        # Find out which locales does the app provide (for now).
        translated_langs = bm.get_locales_list()

        # We do a redirect rather than rendering in the POST. This way we can get proper
        # URL.
        return redirect(url_for('translate.translate_selectlang', appid=app.unique_id))

    # This was a GET, the app should exist already somehow, we will try to retrieve it.
    elif request.method == "GET":

        appid = request.args.get("appid")
        if appid is None:
            flash("appid not received", "error")

            # An appid is required.
            return redirect(url_for("user.apps.index"))

        app = get_app(appid)
        if app is None:
            return render_template("composers/errors.html",
                                   message="Specified App doesn't exist"), 404

        # Load a BundleManager from the app data.
        bm = BundleManager.create_from_existing_app(app.data)

        spec = bm.get_gadget_spec()

        # Check whether an owner exists. If it doesn't, it means the original owner was deleted.
        # In that case, we make ourselves a new owner.
        # Locate the owner for the App's DEFAULT language.
        ownerApp = _db_get_lang_owner_app(spec, "all_ALL")
        # If there isn't already an owner for the default languages, we declare ourselves
        # as the owner for this App's default language.
        # TODO: NOTE: With the latest changes, this should never happen, because owners are declared
        # for all existing languages by the user who creates the app. It may, however, happen in the future,
        # when we take deletions and such into account.
        if ownerApp is None:
            _db_declare_ownership(app, "all_ALL")
            ownerApp = app


        translated_langs = bm.get_locales_list()


    # The following is again common for both GET (view) and POST (edit).

    # Check ownership. Probably eventually we will remove the ownership check above.
    ownerApp = _db_get_lang_owner_app(spec, "all_ALL")
    if ownerApp == app:
        is_owner = True
    else:
        is_owner = False

    owner = ownerApp.owner
    if not is_owner and owner is None:
        # TODO: Improve this error handling. This should NEVER happen.
        flash("Error: Language Owner is None", "error")
        return render_template("composers/errors.html", message="Internal Error: Language owner is None"), 500


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

    # We pass the autoaccept data var so that it can be rendered.
    # TODO: Optimize this once we have this fully covered with tests.
    data = json.loads(app.data)
    autoaccept = data.get("autoaccept", True)  # We autoaccept by default. Problems may arise if this value changes, because it is used in a couple of places.

    # We pass some parameters as JSON strings because they are generated dynamically
    # through JavaScript in the template.
    return render_template("composers/translate/selectlang.html",
                           app=app, # Current app object.
                           xmlspec=spec, # URL to the App XML.
                           autoaccept=autoaccept,  # Whether the app is configured to autoaccept proposals or not.
                           suggested_target_langs=suggested_target_langs, # Suggested (not already translated) langs
                           source_groups_json=json.dumps(src_groups_dict), # Source groups in a JSON string
                           full_groups_json=json.dumps(full_groups_list), # (To find names etc)
                           target_groups=full_groups_list, # Target groups in a JSON string
                           translated_langs=translated_langs, # Already translated langs
                           is_owner=is_owner, # Whether the loaded app has the "Owner" status
                           owner=owner, # Reference to the Owner
                           proposal_num=proposal_num)  # Number of pending translation proposals
