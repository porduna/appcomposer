import sys
from pyflakes.scripts.pyflakes import main as main_pyflakes


sys.argv = [sys.argv[0], 'appcomposer']
main_pyflakes()
