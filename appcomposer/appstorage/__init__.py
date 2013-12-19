
from flask import request, redirect
from appcomposer.appstorage.api import add_var, get_all_vars, set_var, remove_var, create_app



from appcomposer.login import current_user
from appcomposer import db
from appcomposer.application import app as flask_app
from appcomposer.models import App


@flask_app.route('/appstorage', methods=["GET", "POST"])
def appstorage():
    return "Hello appstorage"


@flask_app.route('/appstorage/new', methods=["GET", "POST"])
def new():
    next_url = request.args.get('next', '') or request.form.get('next', '')
    name = request.args.get("name")
    if name is None:
        return "Missing parameter: name", 400
    owner = current_user()
    app = create_app(name, owner, "dummy", "{'message':'Hello world'}")
    return "Application created"


@flask_app.route('/appstorage/list', methods=["GET", "POST"])
def list():
    apps = App.query.all()

    ret = ""

    for app in apps:
        ret += "[ name: %s; id: %s ]<br>" % (app.name, app.unique_id)

    return ret


# TODO: Very important to secure this (check that the user has priviledges over the specified app).
@flask_app.route('/appstorage/<appid>', methods=["GET", "POST", "DELETE"])
def get(appid):
    app = App.query.filter_by(unique_id=appid).first()
    if app is None:
        return "404: App doesn't exist", 404
    if request.method == "DELETE":
        db.session.delete(app)
        db.session.commit()
    else:
        return app.to_json()


@flask_app.route('/appstorage/test/<appid>', methods=["GET", "POST", "DELETE"])
def test(appid):
    # Remove all existing testvars.
    for v in get_all_vars(appid):
        remove_var(v)

    add_var(appid, "testvar", "Test Value")
    vars = get_all_vars(appid)

    var = set_var(appid, "testvar", "Hello")

    return repr(vars)


@flask_app.route('/appstorage/save', methods=["GET", "POST"])
def save():
    next_url = request.args.get('next')

    appid = request.args.get('appid', '') or request.form.get('appid', '')
    data = request.args.get('data', '') or request.form.get('data', '')

    if not data:
        return "400: Malformed Request. Data not present.", 400

    # Locate the app
    app = App.query.filter_by(unique_id=appid).first()
    if app is None:
        return "404: App doesn't exist. Can't save.", 404

    app.data = data
    app.commit()

    if next_url:
        redirect(next)
    return "App saved"
