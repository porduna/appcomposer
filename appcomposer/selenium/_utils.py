#!/usr/bin/python
# Misc utilities for testing.

import glob
import os
import sys


# These functions are to locate the module path reliably (supposedly).
# From StackOverflow.
def we_are_frozen():
    # All of the modules are built-in to the interpreter, e.g., by py2exe
    return hasattr(sys, "frozen")


def module_path():
    encoding = sys.getfilesystemencoding()
    if we_are_frozen():
        return os.path.dirname(unicode(sys.executable, encoding))
    return os.path.dirname(unicode(__file__, encoding))


def reset_database():
    """
    Removes the sqlite database and creates a new one.
    :return: None
    :rtype: None
    """

    path = module_path()
    basepath = os.path.join(path, "../../")

    try:
        os.remove(os.path.join(basepath, "database.db"))
    except:
        pass

    os.chdir(basepath)
    os.system("alembic upgrade head")