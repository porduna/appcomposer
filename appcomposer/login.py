from flask import session

from .db import db_session
from .models import User

def current_user():
    if not session.get("logged_in", False):
        return None
    
    return db_session.query(User).filter_by(login = session['login']).first()
    

