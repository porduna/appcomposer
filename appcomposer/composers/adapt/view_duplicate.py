from flask import render_template, request, url_for, redirect
from wtforms import TextField
from wtforms.validators import Required, Length
from appcomposer.appstorage.api import get_app, update_app_data, get_app_by_name, add_var, create_app
from appcomposer.babel import lazy_gettext
from appcomposer.composers.adapt import adapt_blueprint
from appcomposer.csrf import verify_csrf
from appcomposer.login import requires_login
from flask_wtf import Form


class DuplicationForm(Form):
    name = TextField(lazy_gettext('Name'), validators=[Required(), Length(min=4)])


@adapt_blueprint.route("/duplicate/<appid>/", methods=['GET', 'POST'])
@requires_login
def adapt_duplicate(appid):
    app = get_app(appid)
    if app is None:
        return render_template("composers/errors.html", message="Application not found")

    form = DuplicationForm()

    if form.validate_on_submit():

        # Protect against CSRF attacks.
        if not verify_csrf(request):
            return render_template("composers/errors.html",
                                   message="Request does not seem to come from the right source (csrf check)"), 400

        existing_app = get_app_by_name(form.name.data)
        if existing_app:
            if not form.name.errors:
                form.name.errors = []
            form.name.errors.append(lazy_gettext("You already have an application with this name"))
        else:
            new_app = create_app(form.name.data, 'adapt', app.data)
            for appvar in app.appvars:  # Copy every appvar for the original app as well.
                add_var(new_app, appvar.name, appvar.value)

            return redirect(url_for('.adapt_edit', appid=new_app.unique_id))

    if not form.name.data:
        counter = 2
        potential_name = ''
        while counter < 1000:
            potential_name = '%s (%s)' % (app.name, counter)

            existing_app = get_app_by_name(potential_name)
            if not existing_app:
                break
            counter += 1

        form.name.data = potential_name

    return render_template("composers/adapt/duplicate.html", form=form, app=app)