import datetime
from appcomposer import db
from appcomposer.login import create_salted_password
from appcomposer.models import User, App, AppVar


def create_user(login, name, password):
    """
    Creates a new user and adds it to the DB.
    """
    password = create_salted_password("password")
    user = User(login, name, password, "user@user.com", None, None,
                datetime.datetime.now(), datetime.datetime.now(), "userpass", password)
    db.session.add(user)
    db.session.commit()
    return user


def remove_user(user):
    """
    Deletes a user from the DB.

    @param user: User object. It is *NOT* a login string. If None then nothing is done.
    """
    if user is None:
        return None

    # Get every AppVar and App for the user.
    apps = App.query.filter_by(owner=user).all()
    for app in apps:
        appvars = AppVar.query.filter_by(app=app).all()
        for var in appvars:
            db.session.delete(var)
        db.session.delete(app)

    db.session.delete(user)
    db.session.commit()
    return None


def get_user_by_login(login):
    """
    Retrieves a user from the DB by its login.
    """
    return User.query.filter_by(login=login).first()


