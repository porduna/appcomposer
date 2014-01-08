"""
Support external plug-ins without dealing with package or directory problems.
Doing:

  from appcomposer.composers.adapt.ext.edt import foo

Will internally do:

  from golab_adapt_edt import foo

We use the flask.exthook to do this.
"""

def setup():
    from flask.exthook import ExtensionImporter
    importer = ExtensionImporter(['golab_adapt_%s'], __name__)
    importer.install()


setup()
del setup

