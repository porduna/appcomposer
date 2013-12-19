from flask import redirect, url_for
from flask.ext.admin import BaseView, expose

class RedirectView(BaseView):

    def __init__(self, redirection_url, *args, **kwargs):
        self.redirection_url = redirection_url
        super(RedirectView, self).__init__(*args, **kwargs)

    @expose()
    def index(self):
        return redirect(url_for(self.redirection_url))
