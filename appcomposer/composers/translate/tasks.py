"""
We will define Celery tasks here.
"""
from appcomposer.application import celery_app
from appcomposer.composers.translate.bundles import BundleManager

import requests


@celery_app.task(bind=True)
def extract_opensocial_app(self, appurl):
    """
    Task for requesting every file from the external server.
    Returns the JSON describing the BundleManager for the new app.
    The App is *not* added to the DB automatically.
    """

    def app_extraction_progress_callback(done, total, message):
        self.update_state(state='PROGRESS', meta={'done': done, 'total': total, 'message': message})

    bm = BundleManager.create_new_app(appurl, app_extraction_progress_callback)

    return bm.to_json()


if __name__ == "__main__":
    ar = extract_opensocial_app.delay("")
    print ar.result