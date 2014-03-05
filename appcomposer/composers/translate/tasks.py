"""
We will define Celery tasks here.
"""
from appcomposer.application import celery_app

import requests


@celery_app.task
def extract_opensocial_app(spec_url):
    return "{}"




if __name__ == "__main__":
    ar = extract_opensocial_app.delay("http://www.google.com")
    print ar.result