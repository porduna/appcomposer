"""
Contains exceptions that the OPERATIONS layer may throw.
"""


class AppNotFoundException(Exception):
    """
    Exception to be thrown when the an App wasn't found.
    """

    def __init__(self, message=None):
        self.message = message


class InternalError(Exception):
    """
    Exception to be thrown when internal errors which shouldn't happen do happen.
    """
    def __iadd__(self, message=None):
        self.message = message