"""
Common exceptions to be used in the module.
"""
from appcomposer.babel import gettext


class ParameterNotProvidedException(Exception):
    """
    Exception to be thrown when an endpoint expects a GET or POST parameter that was not
    provided.
    """

    def __init__(self, parameter_name):
        """
        :param parameter_name: Name of the parameter that was not provided.
        """
        self.message = "Parameter %s was not provided" % parameter_name


class InvalidCSRFException(Exception):
    """
    Exception to be thrown when the CSRF check fails.
    """

    def __init__(self):
        """
        :return:
        """
        self.message = gettext("Request does not seem to come from the right source (csrf check)")