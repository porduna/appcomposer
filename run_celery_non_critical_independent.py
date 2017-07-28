#!/usr/bin/python
from appcomposer.translator.tasks import cel
import sys

cel.worker_main(sys.argv + ['--concurrency=2', '--queues=non-critical-independent-tasks'])
