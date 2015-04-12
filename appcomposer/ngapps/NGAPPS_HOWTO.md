
The 'ngapps' system is relatively complex and is meant to allow the somewhat simultaneous use of a typical
Flask/Python workflow with a typical Grunt/Bower/Angular workflow. It has the following aims:

  * The Angular SPAs should be as independent from the Flask server-generated pages
  as possible.
  * It should be possible to develop the Angular SPAs using Grunt facilities such as auto-reload, etc.
  * In production, the code should be minificable.
  * The translations should be handled by the Flask server, as opposed to the client-side Angular way (so that the
  workflow for translations is common to the Flask pages).
  * The application should be integrable within a Flask/Jinja2 template, to respect the original UX of the Flask pages.
  * In production, it should be possible to eventually serve the angular files statically (through Apache rather than Flask).


When trying to meet all these requirements some problems have had to be solved.


## App integrable within Jinja2 and Translations handled by Flask

Because the apps need to be integrable within Jinja2, it is not possible to simply place all the app within the
**static** folder and serve it independently from Flask. A possible solution would be to use an iframe. However, iframes
are generally somewhat problematic by themselves. Also, translations need to be provided by Flask somehow, so
simply a redirection wouldn't be possible.

A seemingly valid alternative would be to place the whole App within the **templates** folder rather than the **static**
one. This would at least two problems:

  * The default Angular and Jinja2 template syntax would conflict.
  * It would be inefficient because there would be no static files at all, and no easy way to serve them statically.


## Solution

The current system works in the following way:

There is an **ngapps* folder. This folder is meant to contain each app. Each app can be a standard Node/Grunt/Bower/Angular
app. This full server is not served either statically or dynamically. Only some files within will be.

Within each app, the index.html file is a Jinja2 file. This file will be rendered as a Jinja2 template, even though it is
designed to be compatible with the various Grunt tools, such as those for minification. In fact, the template can be
minified just fine, and the index.html that will be *rendered* in production would be a minified version of it.
Because this file is a Jinja2 template, it is fully integrated with the rest of the Flask pages and we can render
the translation information into this page (which will be used by the Angular app).

Every other file in the App is meant to be served statically, and no Jinja2 template rendering is involved. Thus,
Angular template syntax can be freely used, and these files can be served statically.


## Workflow

The workflow for development is meant to be the standard Node/Grunt one.

`grunt serve` will run the Flask application, go to the App's URL, and start serving everything. Flask replaces the
*connect* nodejs-powered server that is typically used.

If NGAPPS_DEV_MODE flag is enabled, Flask serves files from two folders:
`app` and `.tmp`, and ensures that app/index.html is rendered through Jinja2.

Otherwise, Flask will serve only from the `dist` folder.

`grunt build` will apply the build procedure to all the files and output the result in dist.


## Serving pages

To be able to serve the right URLs depending on the settings there is a relativize_url filter in the
index.html Jinja2 template. This can be used to specify the folder from which the static files will be
served, and the URLs for this files can still be added automatically by the Grunt tools.
