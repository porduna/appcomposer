"""
Contains exceptions that the OPERATIONS layer may throw.
"""
from appcomposer.babel import gettext


class AppNotFoundException(Exception):
    """
    Exception to be thrown when the an App wasn't found.
    """

    def __init__(self, message=None):
        self.message = gettext("Specified App doesn't exist")


class InternalError(Exception):
    """
    Exception to be thrown when internal errors which shouldn't happen do happen.
    """

    def __iadd__(self, message=None):
        self.message = gettext("Internal Error")


class AppNotValidException(Exception):
    """
    For any reason, the App is not valid.
    """

    def __init__(self, message=None):
        self.message = gettext("The application does not seem to be valid")