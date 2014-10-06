

from flask import Flask, Response, request
import pprint

app = Flask(__name__)

@app.route("/test")
def test():
    str = pprint.pformat(request.environ, depth=5)
    return Response(str, mimetype="text/text")

app.run(debug=True)