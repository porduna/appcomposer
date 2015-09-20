import json
from flask import Response
from appcomposer.login import requires_login
from appcomposer.composers.adapt import adapt_blueprint

@adapt_blueprint.route("/appslist_proxy", methods=["GET"])
@requires_login
def appslist_proxy():
    """
    Retrieves a list of the App repository through the external GoLabz API.
    Returns the list in JSON.
    """

    # For now, if the user specifically wants adaptable Apps we return a hard-coded list.
    adapt_list = [
        {
            "title": "Concept Mapper",
            "author": "admin",
            "description": "<p class=\"p1\">The Concept Mapper tool lets you create concept maps, to get an overview of the key concepts and their relations in a scientific domain. Key concepts can be pre-defined to support the learner.</p>",
            "app_url": "http://go-lab.gw.utwente.nl/production/conceptmapper_v1/tools/conceptmap/src/main/webapp/conceptmapper.xml",
            "app_type": "OpenSocial gadget",
            "app_image": "http://www.golabz.eu/sites/default/files/images/app/app-image/conceptmap.png"
        },
        {
            "title": "Hypothesis Tool",
            "author": "govaerts",
            "description": "<p>This app allows to create hypotheses</p>",
            "app_url": "http://go-lab.gw.utwente.nl/production/hypothesis_v1/tools/hypothesis/src/main/webapp/hypothesis.xml",
            "app_type": "OpenSocial gadget",
            "app_image": "http://www.golabz.eu/sites/default/files/images/app/app-image/Hypo%20tool.png"
        }
    ]

    ret = json.dumps(adapt_list)
    return Response(ret, mimetype="application/json")
