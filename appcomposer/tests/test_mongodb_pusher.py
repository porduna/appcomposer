#!/usr/bin/python

import datetime

from appcomposer.composers.translate import mongodb_pusher as pusher


class TestMongoDBPusher:
    def __init__(self):
        pass

    def test_connection(self):
        assert pusher.cli.alive()

    def test_mongodb_pusher(self):
        t = datetime.datetime.utcnow()
        pusher.push.apply(args=["app.xml", "test_TEST_TEST", "test data", t])

        testbundle = pusher.bundles.find_one({"bundle": "test_TEST_TEST", "spec": "app.xml"})
        assert testbundle["bundle"] == "test_TEST_TEST"
        assert testbundle["spec"] == "app.xml"

        print testbundle["time"]
        assert abs((t - testbundle["time"]).seconds < 1)
        assert testbundle["data"] == "test data"

    def test_nothing(self):
        pass

    def tearDown(self):
        pass
        #pusher.bundles.remove({"bundle": "test_TEST_TEST"})