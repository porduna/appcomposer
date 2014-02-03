from flask import request, render_template
from appcomposer.composers.translate import translate_blueprint, UrlForm


@translate_blueprint.route('/', methods=['GET', 'POST'])
def translate_index():
    form = UrlForm(request.form)

    # As of now this should be a just-viewing GET request. POSTs are done
    # directly to selectlang and should actually not be received by this
    # method.
    return render_template('composers/translate/index.html', form=form)