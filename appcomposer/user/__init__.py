import datetime
from appcomposer import db
from appcomposer.models import User


def create_user(login, name, password):
    """
    Creates a new user and adds it to the DB.
    """
    user = User(login, name, password, "user@user.com", None, None,
                datetime.datetime.now(), datetime.datetime.now(), "loginpass", "password")
    db.session.add(user)
    db.session.commit()
    return user


def remove_user(user):
    """
    Deletes a user from the DB.

    @param user: User object. It is *NOT* a login string.
    """
    db.session.delete(user)
    db.session.commit()
    return None


def get_user_by_login(login):
    """
    Retrieves a user from the DB by its login.
    """
    return User.query.filter_by(login=login).first()


