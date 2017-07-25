#!/usr/bin/python
from appcomposer.translator.tasks import cel
import sys

# Run all the queues in one
cel.worker_main(sys.argv + ['--beat', '--loglevel=INFO', '--concurrency=1', '--queues=single-sync-tasks,non-critical-independent-tasks,critical-independent-tasks,slow-independent-tasks'])
