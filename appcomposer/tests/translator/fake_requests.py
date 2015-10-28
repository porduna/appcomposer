import mock
import json
import requests

def _response(contents):
    r = requests.Response()
    r._content = contents
    return r

APPS = []

for app_id in range(10):
    APPS.append({
        "title": "APP%s" % app_id,
        "id": "%s" % app_id,
        "author": "admin",
        "description": "DESCRIPTION%s" % app_id,
        "app_url": "http://url%s/gadget.xml" % app_id,
        "app_type": "OpenSocial gadget",
        "app_image": "http://www.golabz.eu/logo%s.png" % app_id,
        "app_thumb": "http://www.golabz.eu/logo_thumb%s.png" % app_id,
        "app_golabz_page": "http://www.golabz.eu/apps/page%s" % app_id
    })

LABS = []


SIDE_EFFECT = {
    "http://www.golabz.eu/rest/apps/retrieve.json": _response(json.dumps(APPS)),
    "http://www.golabz.eu/rest/labs/retrieve.json": _response(json.dumps(LABS)),
}

def create_requests_mock():
    return mock.MagicMock(side_effect = lambda url, *args, **kwargs: SIDE_EFFECT.get(url))

