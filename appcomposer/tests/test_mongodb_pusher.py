#!/usr/bin/python

import datetime

from appcomposer.composers.translate import mongodb_pusher as pusher
from appcomposer.composers.translate.bundles import Bundle
from appcomposer.composers.translate.updates_handling import on_leading_bundle_updated


class TestMongoDBPusher:
    def __init__(self):
        pass

    def test_connection(self):
        assert pusher.cli.alive()

    def test_mongodb_pusher(self):
        t = datetime.datetime.utcnow()
        pusher.push.apply(args=["app.xml", "test_TEST_TEST", "test data", t])

        testbundle = pusher.bundles.find_one({"bundle": "test_TEST_TEST", "spec": "app.xml"})
        assert testbundle is not None
        assert testbundle["bundle"] == "test_TEST_TEST"
        assert testbundle["spec"] == "app.xml"

        print testbundle["time"]
        assert abs((t - testbundle["time"]).seconds < 1)
        assert testbundle["data"] == "test data"

    def test_celery_mongodb_pusher(self):
        """
        Tests that the pusher works, including celery. RabbitMQ and the Celery worker must be running before
        running this test.
        """
        # Create a test bundle
        b = Bundle("test", "CELERYTEST", "ALL")
        async_result = on_leading_bundle_updated("test_app.xml", b)

        # Wait for the async task to finish. This is normally not done.
        async_result.wait()

        testbundle = pusher.bundles.find_one({"bundle": "test_CELERYTEST_ALL", "spec": "test_app.xml"})
        assert testbundle is not None
        assert testbundle["bundle"] == "test_CELERYTEST_ALL"
        assert testbundle["spec"] == "test_app.xml"

    def test_mongodb_pusher_at_app_creation(self):
        # TODO
        pass

    def test_mongodb_pusher_at_app_edit(self):
        # TODO
        pass


    def test_nothing(self):
        pass

    def tearDown(self):
        pusher.bundles.remove({"bundle": "test_TEST_TEST"})
        pusher.bundles.remove({"bundle": "test_CELERYTEST_ALL"})