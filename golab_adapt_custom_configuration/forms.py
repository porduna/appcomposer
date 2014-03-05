from flask.ext.wtf import Form, fields, validators
from wtforms import TextField
from wtforms.validators import Required, EqualTo

class UrlForm(Form):    
    appurl = fields.TextField(validators=[validators.required()])  

    def validate_appurl(self, field):
        appurl = self.get_appurl()

        if appurl is None:
            raise validators.ValidationError('Invalid URL')

    def get_appurl(self):
        print self.appurl.data, "here"
