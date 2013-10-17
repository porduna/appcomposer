from flask.ext.wtf import Form, fields, validators
from wtforms import TextField
from wtforms.validators import Required, EqualTo
#from wtformsparsleyjs import IntegerField, BooleanField, SelectField, TextField

class UrlForm(Form):
    #appurl = TextField('appurl', [Required()])
    
    appurl = fields.TextField(validators=[validators.required()])  

    def validate_appurl(self, field):
        appurl = self.get_appurl()

        if appurl is None:
            raise validators.ValidationError('Invalid URL')

    def get_appurl(self):
        print self.appurl.data, "here"

class LangselectForm(Form):
    sourcelang = TextField('sourcelang', [Required()])
    targetlang = TextField('targetlang', [Required()])    

