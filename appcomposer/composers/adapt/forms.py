from flask.ext.wtf import Form, fields, validators
from wtforms import TextField
from wtforms.validators import Required, EqualTo
#from wtformsparsleyjs import IntegerField, BooleanField, SelectField, TextField

class AdaptappCreateForm(Form):

    domain_data = TextField('domain_data', [Required()])
    experiment_data = TextField('experiment_data', [Required()])    

