.. _installation:

Installation
------------

This section covers the installation and deployment of a custom AppComposer server.


Introduction & Technologies
...........................

The AppComposer is a Web application. It is Open Source and its repository is available at http://github.com/porduna/appcomposer.  

It is based on the python-flask microframework, and also relies on other technologies such as Twitter Bootstrap.

The AppComposer itself is cross-platform, and should be able to run on almost any system where Python and its key packages are available.
However, this guide focuses on deployment on Linux systems. Most of the logic and principles, however, will apply to Windows servers as well,
and certain tips will be included.

Prerrequisites
..............

The prerrequisites are the following:

* Apache Web Server
* MySQL
* Python 2.7.X
* PIP (Python Package Index)
* Several python PIP packages

In Linux
++++++++

Most Linux distributions will have these packages available in their repositories, or even preinstalled. 
In Ubuntu, for instance, you can:

.. code-block:: bash

   sudo apt-get install apache2
   sudo apt-get install mysql-server
   sudo apt-get install python2.7
   sudo apt-get install python-pip


In Windows
++++++++++

In Windows you will most likely have to manually download and install these packages.
 
For Apache2 and MySQL, for instance, you can download XAMPP: http://www.apachefriends.org/es/xampp.html.

Python from: http://www.python.org.

PIP is relatively hard to install. The easiest way is probably to download the appropriate package from http://www.lfd.uci.edu/~gohlke/pythonlibs/, though be warned that it's not an official repository.


Preliminary system configuration
................................

You will most likely want to create a new system user dedicated to running the AppComposer. This is recommended for both cleanness and security.
Throughout this guide, we will assume that you have created an "appcomp" user, with its home at "/home/appcomp", though only minor changes
would be required for different setups.


Obtaining the source code
.........................

The first step required for deployment is to download the project itself. For this, you must have or install Git first. 
Git can be obtained from http://git-scm.com, where you can also find specific instructions for each OS.

Once you have Git, you can clone (download) the project through the following command:

.. code-block:: bash

   git clone https://github.com/porduna/appcomposer.git

That will create an appcomposer folder wherever you are executing your command from.
In these docs, our appcomposer folder will be created at: ``` ~/appcomposer ```.

Specifically, in our case it will be at: ``` /home/appcomp/appcomposer ```, because "appcomp" is the name of our user.

.. note::

    If you were unable to clone the project, please make sure that you have installed Git properly and that the provided URL is indeed accesible.


Additional dependencies & virtualenvs
.....................................

The Appcomposer makes use of Python virtualenvs. To install these you need to:

.. code-block:: bash

   pip install virtualenv

If on Linux, after this:

.. code-block:: bash

   pip install virtualenvwrapper

If on Windows:

.. code-block:: bash

   pip install virtualenvwrapper-win

Once these tools are installed, you can proceed to create the actual virtualenv:

.. code-block:: bash

   mkvirtualenv app
   workon app

Now we should be on the new "app" virtualenv. This is where we will install the dependencies.

To install PIP dependencies, making sure you are in the "app" virtualenv and in the appcomposer folder, do the following:

.. code-block:: bash

   pip install -r requirements.txt
   pip install mysql-python

This will install all packages specified in the requirements.txt file, plus the mysql-python package.

.. note:: 

   Unfortunately, installing mysql-python is not supported in Windows without configuring a compiler first, which is not easy.
   You can obtain the package from some unofficial source, or use (and configure) a different database, such as SQLite.
   Using SQLite for production severs is however not recommended. The following sections of the guide will assume that the database is MySQL. 



Creating the database
.....................

Make sure MySQL is installed properly and running on the system.
Connect to the instance:

.. code-block:: bash

   mysql -u root -p


Now you can create a new database and a new user for the AppComposer:

.. code-block:: bash

   CREATE USER 'appcomp-user'@'localhost' IDENTIFIED BY 'appcomposer';
   CREATE DATABASE appcomp DEFAULT CHARSET `utf8`;
   GRANT ALL PRIVILEGES ON appcomp.* TO 'appcomp-user'@'localhost' IDENTIFIED BY 'appcomposer';

Now, we will need to edit the appcomposer configuration file to refer to our new database. An example for this file is provided in appcomposer/config.py.dist.

To create your own, just copy config.py.dist and name it config.py. It should remain in the appcomposer/ folder. In Linux, from the appcomposer folder,  you can do:

.. code-block:: bash

   cp config.py.dist config.py

Edit the config.py file. With the DB name that we chose, the file should contain something similar to the following:

.. code-block:: python

   DBNAME = 'appcomp'
   DBUSER = 'appcomp-user'
   DBPASSWORD = 'appcomposer'

   SQLALCHEMY_ENGINE_STR = 'mysql://%(user)s:%(password)s@localhost/%(dbname)s' % dict(user = DBUSER, password = DBPASSWORD, dbname = DBNAME)
   USE_PYMYSQL = False   

Now that we have a user and a database, we will need to populate it with actual tables. For this the Appcomposer relies on Alembic. This tool should have been automatically installed through the previous steps.

Now, making sure you are in the appcomposer folder, and that you are in the "app" virtualenv, run the following command:

.. code-block:: python

   alembic upgrade head

This should populate your database and output information about different revisions.

.. note:: 

   For the previous step to work, you will need to have configured and installed everything properly. If it fails, make sure you can check every item in the following checklist:
   
      * I am in the "app" virtualenv (The commandline should show an ```(app)``` before every command).
      * The "alembic" tool can be found (Should have been installed through the previous "pip install -r requirements.txt" step).
      * The MySQL database and user that I have chosen match those specified in the config.py file.
      * I have a config.py file in the appcomposer folder, which is where I have applied my configuration.
      * I am not confusing config.py.dist (which shouldn't have been edited at all) with the config.py file.
      * The Python version that I can run from commandline is 2.7.X (check through "python --version").


Configuring Apache
..................

The AppComposer has been designed to run through the Apache web server, though actually any server capable of running
python web services should be able to run the WSGI. In this guide we will assume that Apache is your chosen server,
but it should be relatively easy to adapt it for different ones.

Before configuring the AppComposer, please make sure that you have mod_wsgi enabled in Apache. You might have to install and/or enable that module separatedly.


Open the Apache configuration ( httpd.conf under most systems ) and append the following settings:

.. note::
   # AppComposer settings
   WSGIDaemonProcess appcomposer-appcomp user=appcomp group=appcomp threads=5 python-path=/home/appcomp/.virtualenvs/app/lib/python2.7/site-packages/
   WSGIScriptAlias /appcomposer /home/appcomp/appcomposer/run_wsgi.wsgi
   WSGIRestrictStdout Off
   WSGIPassAuthorization On

Note that in the snippet above we make several assumptions, which may or may not be true in your case:
   
   * That the user you want to run the AppComposer from, and that you have been using throughout this guide, is named "appcomp".
   * That you want to access the appcomposer from ``http://<yoururl>/appcomposer``
   * That your appcomposer root folder is located at /home/appcomp/appcomposer

If any of these don't apply, then you will need to adapt your configuration accordingly.


With this done, once you restart Apache you should be able to see the AppComposer running at: ``http://<your-url>/appcomposer``










