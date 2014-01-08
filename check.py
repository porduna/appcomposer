import sys, glob
from pyflakes.scripts.pyflakes import main as main_pyflakes

adapt_plugins = glob.glob("golab_adapt_*")

sys.argv = [sys.argv[0], 'appcomposer']
sys.argv.extend(adapt_plugins)
main_pyflakes()
