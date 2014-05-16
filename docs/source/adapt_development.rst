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
<http://www.python.org/>`_, as well as HTML5, is required. Prior knowledge of
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

Tutorial
^^^^^^^^

So as to put a simple example, let's start by a simple example over which we
iterate. Let's imagine a very simple adaptor where the teacher is expected to
write some words and the student will simply see those words. It's not a very
useful example, but covers all the remarkable points. So let's call it
``simpletext``.

Step 1: Register the adaptor
############################

First, let's create the adaptor structure. So as to do this, create the
following three directories and ``__init__.py`` file::

    + golab_adapt_simpletext/
      - __init__.py
      + static/
      + templates/
        + simpletext/

And in the ``__init__.py`` file let's put the following code:

.. code-block:: python

    from appcomposer.composers.adapt import create_adaptor

    adaptor = create_adaptor('Simple text')

    @adaptor.edit_route
    def edit(app_id):
        return "Hi there!"

The ``golab_adapt_simpletext`` directory should be in some point of the
``PYTHONPATH``, which can simply be the same directory where you have the App
Composer deployed (the same directory where you have the ``run.py`` file). Then,
register the adaptor by changing the ``ADAPT_PLUGIN`` variable of the
``config.py`` file::

    ADAPT_PLUGINS = ['simpletext']

At this point, the plug-in should be correctly registered. Start the development
server (run.py), and when going to the Adapt Composer, you should see the
Simple Text adaptor in the list of adaptors:

.. image:: /_static/simpletext1.png
   :width: 400 px
   :align: center

If you build an application with it, once you have provided a name and a
description, you should see the following:

.. image:: /_static/simpletext2.png
   :width: 600 px
   :align: center

Ok, not very exciting. But at least you see that the adaptor has been
successfully installed. Furthermore, you see that anything you put in the edit
method will be returned to the client. You could provide an HTML code there and
it would be displayed every time. However, instead of that, it's better to use a
separate template. So as to do this, we use `Jinja2
<http://jinja.pocoo.org/docs/>`_, which supports some features we are going to
use, such as inheritance or passing the required values.

Step 2: Our first template
##########################

So let's make our first template, which we will save in
``templates/simpletext/edit.html``:

.. code-block:: html

    <html>
        <body style="background: #afa">
            Hi there in a template!
        </body>
    </html>

And let's change the ``__init__.py`` to index it. Note that we import the 
``render_template`` method from Flask:

.. code-block:: python

    from flask import render_template

    from appcomposer.composers.adapt import create_adaptor

    adaptor = create_adaptor('Simple text')

    @adaptor.edit_route
    def edit(app_id):
        return render_template("simpletext/edit.html")


If you're running the App Composer in development mode, you should not need to 
restart the server (since it's restarted automatically once you see that 
``__init__.py`` has been changed). The result is a page that you could see in the 90's:

.. image:: /_static/simpletext3.png
   :width: 400 px
   :align: center

Step 3: Using static resources
##############################

So we should improve this. We're working on this page, so what's more of the 90's than 
a "page under construction" logo? Let's take this one:

.. image:: /_static/simpletext_under_construction.png
   :width: 100 px
   :align: center

And let's put it in the ``static`` directory with the name ``under_construction.png``. 
How do we refer to this file from the template? Easy:

.. code-block:: html

    <html>
        <body style="background: #afa">
            Hi there in a template!
            <img src="{{ url_for('simpletext.static', filename='under_construction.png') }}">
        </body>
    </html>

.. note::
    
    Everything put in the ``static`` directory will automatically be public.

Great, now we have a new old web page!

.. image:: /_static/simpletext4.png
   :width: 400 px
   :align: center

Just to recall the current status, we now have the following structure::

    + golab_adapt_simpletext/
      - __init__.py
      + static/
        - under_construction.png
      + templates/
        + simpletext/
          - edit.html

Step 4: Inheriting from the Adaptor Composer template
#####################################################

However, we probably want a better website, not only with bootstrap, but with the rest of 
the App Composer structure. To make this possible, we are going to extend from an existing
template rather than do our own template from scratch. For this, in the ``edit.html`` we 
are going to change the contents for the following:

.. code-block:: jinja

    {% set title = "Edit a simple text" %}
    {% set adaptor_type = "Simple text" %}                                                                
    {% extends 'composers/adapt/edit.html' %}                                                             
                                                                                                          
    {% block edit_tab %}                                                                                  
        <div class="col-lg-10" style="background: #afa">                                                  
            Hi there in a template!                                                                       
            <img width="100px" src="{{ url_for('simpletext.static', filename='under_construction.png') }}">
        </div>                                                                                            
    {% endblock %}                                                                                        

    {% block preview_tab %}                                                                               
        <div class="col-lg-10" style="background: #afa">                                                  
            Hi there in a template!
            <img width="100px" src="{{ url_for('simpletext.static', filename='under_construction.png') }}">
        </div>
    {% endblock %} 

Basically, we are defining that we are inheriting from ``composers/adapt/edit.html``, where the title should be
``Edit a simple text``, the adaptor_type is ``Simple text``, and in the ``edit`` tab we want to put the same 
content as we used to have, and the same for the ``preview`` tab. As you may notice, we're using Bootstrap 3, 
so we have suddenly advanced around fifteen years.

.. image:: /_static/simpletext5.png
   :width: 400 px
   :align: center

Step 5: First form
##################

Now, if we recall, this adaptor was based on that teachers could add text and
students would be able to see it. The first step to achieve this is to provide a
form and store its contents. So let's change the template, in the ``edit_tab``
and ``preview_tab`` contents, by the following:

.. code-block:: jinja

    {% set title = "Edit the app content" %}
    {% set adaptor_type = "Simple text" %}
    {% extends 'composers/adapt/edit.html' %}

    {% block edit_tab %}
        <div class="col-lg-10">
            <form class="form" action="." method="POST" >
                <input type="text" name="simple_text" value="{{ value }}"/>
                <input type="submit" class="btn btn-primary" value="Submit"/>
            </form>
        </div>
    {% endblock %}

    {% block preview_tab %}
        <div class="col-lg-10">
            The teacher said: {{ value }}
        </div>
    {% endblock %}

As you see, there is a ``{{ value }}``. If the variable does not exist, Flask
simply renders an empty string, so it's not a problem. The result is the following:

.. image:: /_static/simpletext6.png
   :width: 400 px
   :align: center

Time to change the Python code to be aware of this. Note that ``request`` has been imported from ``flask``:

.. code-block:: python

    from flask import render_template, request

    from appcomposer.composers.adapt import create_adaptor

    adaptor = create_adaptor('Simple text')

    @adaptor.edit_route
    def edit(app_id):
        value = ""
        if request.method == 'POST':
            value = request.form['simple_text']
            print value
        return render_template("simpletext/edit.html", value = value)

In the console where you have the ``python run.py`` process being executed
you'll be able to see the messages submitted in the web browser. And every time
you post a message, that message should be shown.

.. warning::

    This example is not taking into consideration CSRF attacks for the sake of
    simplicity. You may check the
    `Flask-WTF documentation <https://flask-wtf.readthedocs.org/en/latest/>`_ on
    automatic ways to avoid it.

Step 6: Saving information in the database
##########################################

Until this point, if you refresh the application, you will start again. But
you should want to save the information in the database. To do so, the
``adaptor`` variable counts with two methods (``load_data`` and ``save_data``)
which work with Python code that they serialize to JSON. By default, this is a
dictionary. Here is how we could use it in this case:

.. code-block:: python

    from flask import render_template, request

    from appcomposer.composers.adapt import create_adaptor

    adaptor = create_adaptor('Simple text', 
                    initial = {'simple_text' : 'No text'})

    @adaptor.edit_route
    def edit(app_id):
        # Load data from the database for this application
        data = adaptor.load_data(app_id)

        if request.method == 'POST':
            value = request.form['simple_text']
            data['simple_text'] = value
            # Store it in the database
            adaptor.save_data(app_id, data)
        
        return render_template("simpletext/edit.html", 
                                    value = data['simple_text'])

Notes on this code:

 * It has changed the call to ``create_adaptor``, providing the default value
   that will be used every time that a new adaptation is made. This way, the
   database will have a dictionary with a field ``simple_text``.

 * It calls the ``load_data`` and ``save_data`` with the ``app_id``. The
   ``load_data`` can be called by any user. But the ``save_data`` can only be
   called by the owner of the application or by the administrators. Other users
   will receive an exception.

If you test this code, by default it will not work, since you are running an
existing application, which had an empty dictionary in the database. If you're
just developing, you should delete your current application and create a new
application. Or you can do something like the following to make it backwards
compatible:

.. code-block:: python

    @adaptor.edit_route
    def edit(app_id):
        # Load data from the database for this application
        data = adaptor.load_data(app_id)

        # If data does not have 'simple_text', add the default value.
        if 'simple_text' not in data:
            data['simple_text'] = 'No text'

At this point, you can already save applications and preview them:

.. image:: /_static/simpletext7.png
   :width: 300 px
   :align: center

.. image:: /_static/simpletext8.png
   :width: 300 px
   :align: center

Step 7: Exporting the application
#################################

Now, we have the application running, but we can not consume it from `Graasp
<https://graasp.epfl.ch/>`_. What we need is other URL that can be consumed by
other systems. We can create a new template for this, adding the following code
to the ``__init__.py`` code at the end of the file. Note that the
``render_template`` of the ``edit`` method now also includes the ``app_id``.

.. code-block:: python

    from flask import render_template, request

    from appcomposer.composers.adapt import create_adaptor

    adaptor = create_adaptor('Simple text',
                    initial = {'simple_text' : 'No text'})

    @adaptor.edit_route
    def edit(app_id):
        # Load data from the database for this application
        data = adaptor.load_data(app_id)

        # If data does not have 'simple_text', add the default value.
        if 'simple_text' not in data:
            data['simple_text'] = 'No text'

        if request.method == 'POST':
            value = request.form['simple_text']
            data['simple_text'] = value
            # Store it in the database
            adaptor.save_data(app_id, data)

        return render_template("simpletext/edit.html",  
                                    value = data['simple_text'],
                                    app_id = app_id)

    @adaptor.route('/export/<app_id>/app.xml')
    def app_xml(app_id):
        data = adaptor.load_data(app_id)
        return render_template("simpletext/app.xml",
                                    value = data['simple_text'])


Which establishes that there is a new URL that can receive a parameter ``app_id`` 
with the application identifier, loads the data and renders a template called ``app.xml``.

So we have to create this template, putting the following code in the ``templates/simpletext/app.xml`` file:

.. code-block:: xml

    <Module>
        <ModulePrefs title="{{ title }}">                                                                 
            <Require feature="osapi" />                                                                   
        </ModulePrefs>                                                                                    
        <Content type="html" view="home,canvas">                                                          
            The teacher said: {{ value }}
        </Content>                                                                                        
    </Module> 

Now we only need to link it in the ``edit.html`` template. We will use the same 
function we used before ``url_for()`` but in a slightly different way: when 
refering routes generated with ``@adaptor.route``, we have to call
``url_for('.app_xml', app_id = 'something')``, being ``app_xml`` the function
name, and ``app_id`` the arguments of the function. See the ``edit.html`` now
(the changes are on the ``preview_tab``):

.. code-block:: jinja

    {% set title = "Edit the app content" %}
    {% set adaptor_type = "Simple text" %}
    {% extends 'composers/adapt/edit.html' %}

    {% block edit_tab %}
        <div class="col-lg-10">
            <form class="form" action="." method="POST" >
                <input type="text" name="simple_text" value="{{ value }}"/>
                <input type="submit" class="btn btn-primary" value="Submit"/>
            </form>
        </div>
    {% endblock %}

    {% block preview_tab %}
        <div class="col-lg-10">
            The teacher said: {{ value }}
            <br>
            <a href="{{ url_for('.app_xml', app_id = app_id) }}">App URL</a>
        </div>
    {% endblock %}

With this, you can see the link in the preview tab, which provides a link to the
final URL that can be added to Graasp.

.. image:: /_static/simpletext9.png
   :width: 300 px
   :align: center

Step 8: Cleaning up
###################

In this simple example, all the HTML code you that will be displayed to the
users is as simple as the following::

    The teacher said: {{ value }}


Which in the previous step, we see that is repeated in the two templates
(``edit.html`` and ``app.xml``). In a real world scenario, this is not
affordable neither can be maintained. The easiest solution is to centralize 
it to a single template.

So we will create a new HTML template file with these contents:

.. code-block:: jinja

    {% macro render_simpletext(value) %}
    The teacher said: {{ value }}
    {% endmacro %}

And change the ``app.xml`` file to import it and call it:

.. code-block:: xml

    <Module>
        <ModulePrefs title="{{ title }}">
            <Require feature="osapi" />
        </ModulePrefs>
        <Content type="html" view="home,canvas">
         <![CDATA[
        {% from "simpletext/_simpletext.html" import render_simpletext %}
        {{ render_simpletext(value) }}
        ]]>
        </Content>
    </Module>

Now, the ``edit.html`` file can also import it (showing only the ``preview_tab`` here):

.. code-block:: jinja

    {% block preview_tab %}
        <div class="col-lg-10">
            {% from "simpletext/_simpletext.html" import render_simpletext %}
            {{ render_simpletext(value) }}
            <br>
            <a href="{{ url_for('.app_xml', app_id = app_id) }}">App URL</a>
        </div>
    {% endblock %}

This way, the code is centralized in a single file, being imported in both. In some 
situations, if the file is too complex or includes more contents, it could be added 
through an iframe from the edit tab. For example, we could create a new template
called ``simpletext.html`` with only the import:

.. code-block:: jinja

    {% from "simpletext/_simpletext.html" import render_simpletext %}
    {{ render_simpletext(value) }}

Add a route for it: 

.. code-block:: python

    @adaptor.route('/export/<app_id>/index.html')
    def index_html(app_id):
        data = adaptor.load_data(app_id)
        return render_template("simpletext/simpletext.html",
                                    value = data['simple_text'])

And in the ``preview_tab`` of the ``edit.html`` file include the iframe:

.. code-block:: jinja

    {% block preview_tab %}
    <div class="col-lg-10">
        <iframe src="{{ url_for('.index_html', app_id = app_id) }}"
            width="750" height="590" frameborder="1px solid gray"
            scrolling="no"></iframe>
        <br>
        <a href="{{ url_for('.app_xml', app_id = app_id) }}">App URL</a>
    </div>
    {% endblock %}

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

