import urllib2
import traceback
import xml.dom.minidom as minidom

import babel
from flask import request, flash, redirect, url_for, render_template, json
from requests.exceptions import MissingSchema

from appcomposer.babel import gettext
from appcomposer.composers.translate.operations import ops_highlevel
from appcomposer.composers.translate.operations.ops_exceptions import AppNotFoundException, InternalError
from appcomposer.composers.translate.operations.ops_highlevel import load_app
from appcomposer.csrf import verify_csrf
from appcomposer.utils import get_original_url
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import BundleManager, InvalidXMLFileException, NoValidTranslationsException
from appcomposer.login import requires_login
from appcomposer.application import app as flask_app


@translate_blueprint.route("/selectlang", methods=["GET", "POST"])
@requires_login
def translate_selectlang():
    """
    Source language & target language selection.

    Different cases when creating an App:
        - Default translation exists; other translations exist -> Created normally
        - Default translation DOES NOT exist or is invalid; english translations exist or is invalid -> English is the default
        - Default translation DOES NOT exist or is invalid; english translation DOES NOT exist or is invalid; other translations exist -> First Other translation is the default
        - Default translation, english translation, and other translations DO NOT exist or are invalid -> NoValidTranslations page; App is not created
    """

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

        # Protect against CSRF attacks.
        if not verify_csrf(request):
            return render_template("composers/errors.html",
                                   message=gettext(
                                       "Request does not seem to come from the right source (csrf check)")), 400

        # URL to the XML spec of the gadget.
        appurl = request.form.get("appurl")
        spec = appurl
        if appurl is None or len(appurl) == 0:
            flash(gettext("An application URL is required"), "error")
            return redirect(url_for("translate.translate_index"))

        base_appname = request.values.get("appname")
        if base_appname is None:
            return render_template("composers/errors.html", message=gettext("An appname was not specified"))

        try:
            # XXX FIXME
            # TODO: this makes this method to call twice the app_xml. We shouldn't need
            # that. We should have the contents here downloaded for later.
            if appurl.startswith(('http://', 'https://')):
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
        appname = ops_highlevel.find_unique_name_for_app(base_appname)
        if appname is None:
            return render_template("composers/errors.html",
                                   message=gettext("Too many Apps with the same name. Please, choose another."))


        # THE FOLLOWING SHOULD PROB BE REPLACED BY A SINGLE LINE (Not counting exception handling).

        # Create a fully new App. It will be automatically generated from a XML.
        try:

            app, bm = ops_highlevel.create_new_app(appname, appurl)

        except NoValidTranslationsException:
            return render_template("composers/errors.html",
                                   message=gettext(
                                       "The App you have chosen does not seem to have any translation. At least a base translation is required, which will often be"
                                       " prepared by the original developer.")
            ), 400
        except InvalidXMLFileException:
            # TODO: As of now, not sure that this exception can actually ever arise. Maybe it should be merged with NoValidTranslationsException.
            return render_template("composers/errors.html",
                                   message=gettext(
                                       "Invalid XML in either the XML specification file or the XML translation bundles that it links to.")), 400
        except MissingSchema:
            return render_template("composers/errors.html",
                                   message=gettext(
                                       "Failed to retrieve the XML spec. The URL was maybe invalid or not available.")), 400

        if len(bm._bundles) == 0:
            # TODO: Consider adding a "go-back" screen / button.
            return render_template("composers/errors.html",
                                   message=gettext(
                                       "The App you have chosen does not seem to have a base translation. The original developer needs to prepare it for internationalization first.")), 400

        flask_app.logger.info("[translate]: App created for %s" % appurl)

        # We do a redirect rather than rendering in the POST. This way we can get proper
        # URL.
        return redirect(url_for('translate.translate_selectlang', appid=app.unique_id))


    # This is again GET code.

    appid = request.args.get("appid")
    if appid is None:
        flash(gettext("appid not received"), "error")

        # An appid is required.
        return redirect(url_for("user.apps.index"))

    try:
        app, bm, owner, is_owner, proposal_num, src_groups_dict, suggested_target_langs, translated_langs, autoaccept = load_app(appid, targetlangs_list)

    except AppNotFoundException:

        return render_template("composers/errors.html",
                           message=gettext("Specified App doesn't exist")), 404

    except InternalError, ex:

        return render_template("composers/errors.html",
                               message=gettext("Internal Error") + ex.message), 500

    # We pass some parameters as JSON strings because they are generated dynamically
    # through JavaScript in the template.
    return render_template("composers/translate/selectlang.html",
                           app=app,  # Current app object.
                           xmlspec=app.spec.url,  # URL to the App XML.
                           autoaccept=autoaccept,  # Whether the app is configured to autoaccept proposals or not.
                           suggested_target_langs=suggested_target_langs,  # Suggested (not already translated) langs
                           source_groups_json=json.dumps(src_groups_dict),  # Source groups in a JSON string
                           full_groups_json=json.dumps(full_groups_list),  # (To find names etc)
                           target_groups=full_groups_list,  # Target groups in a JSON string
                           translated_langs=translated_langs,  # Already translated langs
                           is_owner=is_owner,  # Whether the loaded app has the "Owner" status
                           owner=owner,  # Reference to the Owner
                           proposal_num=proposal_num)  # Number of pending translation proposals
