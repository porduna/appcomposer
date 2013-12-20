.. _adapt_development:

Adapt plug-in development
-------------------------

.. contents:: Table of Contents

The target of this section is to show how to develop new adaptors for the
:ref:`adapt`. The Adapt Composer aims to enable teachers to develop
their own applications easily. So as to do this, it provides a simple model to
develop these applications, which can later be configured by the teacher, and
are once customized they are available to students.

So as to develop new adaptors, some software development skills are required. At
the moment of this writing, basic knowledge of the `Python programming language
<http://www.python.org/>`_, as well as HTML5, is required. Prior knowledge to
these technologies is assumed in this section.

Additionally, it is assumed that the developer has properly installed the App
Composer in debug mode (see :ref:`installation` first).

Introduction
~~~~~~~~~~~~

The Adaptor Composer typically contains of two parts:

 * An *edit* tab, where the teacher is expected to edit the parameters for
   adapting the application.
 * A *preview* tab, where the teacher is expected to see how students will see
   the adapted application.

However, the adaptor developer can implement more tabs or change the structure.
To make the information persistant and share it between the two tabs, the
Adaptor Composer relies on and wraps the App Composer database. This information must
always be a JSON document. The structure of this document is managed by the
adaptor developer. An example for the Concept Mapper would be:

.. code-block:: javascript

    {
        'concepts' : ['concept1', 'concept2', 'concept3']
    }



Developing adaptors with HTML5
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
    We are designing a new approach that would not require any Python code.


Developing adaptors with Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The adaptors API consists in one method to register the adaptor, which returns a
structure that allows developers to easily interact with the database, as well
as to publish documents based on templates and static files.

The system relies on the `Flask micro webdevelopment framework
<http://flask.pocoo.org/docs/>`_, but the adaptor development does not need to
worry too much about the internals of flask. However, there are some methods
used in the following examples which can be found in the Flask documentation,
and the templates use `Jinja2 <http://jinja.pocoo.org/docs/>`_.

Adaptor structure
^^^^^^^^^^^^^^^^^

Developing an adaptor with Python requires creating a directory with the
following minimum contents::

    golab_adapt_myadaptor/

        - __init__.py  (Python code)

        + static/  (files which will be publicly accessible)
            - file1.js
            - file2.js
            - file3.html

        + templates/  (set of files which will be rendered as registered in the
                      Python code)
            - file1.html
            - file2.js

Where the ``golab_adapt_`` prefix is mandatory and ``myadaptor`` is the
identifier of the adaptor.

The ``__init__.py`` file must have the following structure:

.. code-block:: python

    from flask import render_template

    from appcomposer.composers.adapt import create_adaptor

    adaptor = create_adaptor('My Adaptor name', initial = {
            'concepts' : ''
        })

    @adaptor.edit_route
    def edit(app_id):
        # 
        # Some code to see if there is a form, saving information, loading it,
        # etc.
        # 
        # To interact with the database, the following two methods are provided:
        # 
        #    data = adaptor.load_data(app_id)
        #    data['concepts'].append("something")
        #    adaptor.save_data(app_id, data)
        # 
        return render_template("myadaptor/edit.html", app_id = app_id)

    @adaptor.route('/export/<app_id>/')
    def export(app_id):
        data = adaptor.load_data(app_id)

        return render_template("myadaptor/export.html", app_id = app_id, 
                                concepts = data['concepts'])


Finally, in the appcomposer we need to add the following configuration variable in ``config.py``::

    ADAPT_PLUGINS = ['myadaptor']

And restart the App Composer.

My first adaptor
^^^^^^^^^^^^^^^^

So as to put a simple example, let's start by a simple example over which we
iterate. Let's imagine a very simple adaptor where the teacher is expected to
write some words and the student will simply see those words. It's not a very
useful example, but covers all the remarkable points.

First, let's create the plug-in structure

Examples
^^^^^^^^

In the `code repository <https://github.com/porduna/appcomposer/>`_ you have a
couple of running examples.

Feedback
--------

If you have ideas on how to improve this system, please contact us!

Right now we have the following ideas:

 * Creating a simple script that allows developers to do:
   ``appcomposer --new-adaptor=dummy`` and assume that it generates the
   directory structure.

 * Developing a plug-in structure with a simple JavaScript API based on
   load/save that enables developers which do not know Python to develop their
   own systems.

