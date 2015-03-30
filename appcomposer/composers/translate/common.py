"""
Small common operations to be done throughout the module.
"""
from flask import request
from . import exceptions


def get_required_param(name, allow_empty=False):
    """
    Retrieves a required parameter from the request object, or throws an exception if it is not found.
    :param name: The parameter to retrieve.
    :type name: str
    :param allow_empty: If set to false, it will also throw if the parameter is provided but is empty.
    :type allow_empty: bool
    :return: The parameter.
    """
    val = request.values.get(name)
    if val is None:
        raise exceptions.ParameterNotProvidedException(name)
    if not allow_empty and len(val) == 0:
        raise exceptions.ParameterNotProvidedException(name)
    return val