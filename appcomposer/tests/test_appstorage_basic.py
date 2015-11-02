import appcomposer
import appcomposer.application

from appcomposer.tests.utils import LoggedInComposerTest
from appcomposer.appstorage import api
from appcomposer.login import current_user
from appcomposer.models import Spec


class TestAppstorageBasic(LoggedInComposerTest):

    def _cleanup(self):
        """
        Does cleanup tasks in case the tests failed before.
        Can be invoked *before* and *after* the tests.
        """
        app = api.get_app_by_name("UTApp")
        if app is not None:
            api.delete_app(app)
        app = api.get_app_by_name("UTAppDel")
        if app is not None:
            api.delete_app(app)

        # Remove the Spec that may exist.
        spec = api.db.session.query(Spec).filter_by(url="http://myurl.com").first()
        if spec is not None:
            api.db.session.delete(spec)
            api.db.session.commit()


    def test_current_user(self):
        cu = current_user()
        assert cu.login == "testuser"

    def test_getcreate_spec(self):
        """
        Ensures that getcreate works as expected.
        :return:
        """
        spec = api.getcreate_spec("http://myurl.com")
        assert spec is not None

        # Retrieve the spec from the DB.
        spec2 = api.db.session.query(Spec).filter_by(url="http://myurl.com").first()
        assert spec2.id == spec.id

        # getcreate again to ensure the same id is returned
        spec3 = api.getcreate_spec("http://myurl.com")
        assert spec3.id == spec.id

    def test_create_app(self):
        app = api.create_app("UTApp", "dummy", None, "{}")
        assert app is not None
        assert app.name == "UTApp"

        id = app.unique_id  # TODO: Probably no point for App to have two different unique ids.
        app = None
        app = api.get_app(id)
        assert app is not None
        assert app.name == "UTApp"
        assert app.owner == current_user()

    def test_delete_app(self):
        app = api.create_app("UTAppDel", "dummy", None, "{}")
        assert app is not None

        api.delete_app(app)
        app = api.get_app_by_name("UTAppDel")
        assert app is None
