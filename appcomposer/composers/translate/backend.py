from appcomposer.composers.translate import translate_blueprint


class Bundle(object):

    def __init__(self, country, lang, group):
        self.country = country
        self.lang = lang
        self.group = group

        self._msgs = {
            # identifier : translation
        }
    def add_msg(self, word, translation):
        pass


@translate_blueprint.route('/backend', methods=['GET', 'POST'])
def backend():
    return "Backend"
