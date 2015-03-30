from appcomposer.composers.translate3 import translate3_blueprint


@translate3_blueprint.route("/")
def api_():
    return "Translate 3 index"