import urllib2
import traceback
import xml.dom.minidom as minidom

from flask import request, redirect, url_for, render_template
from requests.exceptions import MissingSchema

from appcomposer.composers.translate import exceptions
from appcomposer.babel import gettext
from appcomposer.composers.translate.operations import ops_highlevel, ops_language
from appcomposer.composers.translate.operations.ops_exceptions import AppNotFoundException, InternalError, \
    AppNotValidException
from appcomposer.csrf import verify_csrf
from appcomposer.utils import get_original_url
from appcomposer.composers.translate import translate_blueprint
from appcomposer.composers.translate.bundles import InvalidXMLFileException, NoValidTranslationsException
from appcomposer.login import requires_login
from appcomposer.application import app as flask_app
from appcomposer.composers.translate import common


def handle_selectlang_GET():

    appid = common.get_required_param("appid")

    app, bm, owner, is_owner, proposal_num, autoaccept = ops_highlevel.load_app(appid)

    # Obtain information about the languages that we can translate to.
    # TO-DO: Those will generally be the same so we should consider some way of caching it
    # and calling it once.
    languages = ops_language.obtain_languages()
    groups = ops_language.obtain_groups()

    # Translation info about ownerships etc so that we can render selectlang properly.
    translation_info = ops_highlevel.obtain_translation_info(app)


    # We pass some parameters as JSON strings because they are generated dynamically
    # through JavaScript in the template.
    return render_template("composers/translate/selectlang.html",
                           app=app,  # Current app object.
                           xmlspec=app.spec.url,  # URL to the App XML.
                           autoaccept=autoaccept,  # Whether the app is configured to autoaccept proposals or not.
                           is_owner=is_owner,  # Whether the loaded app has the "Owner" status
                           owner=owner,  # Reference to the Owner
                           proposal_num=proposal_num,
                           languages=languages,
                           groups=groups,
                           translation_info=translation_info)  # Number of pending translation proposals


def handle_selectlang_POST():
    """
    Handles a POST request to selectlang.
    That is a request to create a new application.
    It creates the new application and redirects the user to the GET screen of the same endpoint.
    :return:
    """

    # Protect against CSRF attacks.
    if not verify_csrf(request):
        raise exceptions.InvalidCSRFException()

    # URL to the XML spec of the gadget.
    appurl = common.get_required_param("appurl")
    base_appname = common.get_required_param("appname")

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

    app, bm = ops_highlevel.create_new_app(appname, appurl)
    flask_app.logger.info("[translate]: App created for %s" % appurl)

    # We do a redirect rather than rendering in the POST. This way we can get proper
    # URL.
    return redirect(url_for('translate.translate_selectlang', appid=app.unique_id))


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

    try:

        if request.method == "POST":
            return handle_selectlang_POST()
        else:
            return handle_selectlang_GET()

    except exceptions.ParameterNotProvidedException, ex:
        return render_template("composers/errors.html", message=ex.message), 400
    except AppNotFoundException, ex:
        return render_template("composers/errors.html", message=ex.message), 404
    except InternalError, ex:
        return render_template("composers/errors.html", message=ex.message), 500
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
    except AppNotValidException, ex:
        # The application does not seem to be valid, possibly because it resulted in an app with no bundles.
        return render_template("composers/errors.html",
                               message=ex.message)



# Language information required by this View to be able to render the template:
#
# Languages:
# {
#   'all_ALL': 'DEFAULT',
#   'de_ALL': 'German'
# }
#
# Groups:
# SORTED DICTIONARY
# {
#   '14-18': 'Adolescents'
# }
#
#
# Translations
#
# {
#   'all_ALL': {
#     groups: ['14-18'],
#     owner: 'admin'
#   }
# }




