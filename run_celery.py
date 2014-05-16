#!/usr/bin/python
"""
This script is intended to help run the celery worker.
When running through this script, the celery worker
is automatically passed the -B parameter, which makes it
a celery beat. (For scheduling purposes). This is essentially
so that there is no need to run a separate celery beat.
"""

from appcomposer.composers.translate.mongodb_pusher import cel
import sys

cel.worker_main(sys.argv + ["-B"])