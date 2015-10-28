import mock
import requests

def _response(contents):
    r = requests.Response()
    r._content = contents
    return r

SIDE_EFFECT = {
    "http://www.golabz.eu/rest/apps/retrieve.json": _response("[]"),
    "http://www.golabz.eu/rest/labs/retrieve.json": _response("[]"),
}

def create_requests_mock():
    return mock.MagicMock(side_effect = lambda url, *args, **kwargs: SIDE_EFFECT.get(url))

