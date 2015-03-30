"""
New translator
"""

from flask import Blueprint

from appcomposer import db

translator_blueprint = Blueprint('translator', __name__)

@translator_blueprint.route('/')
def translator_index():
    return "Hi there, this is the new translator"
