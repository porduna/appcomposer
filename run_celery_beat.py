#!/usr/bin/python
from appcomposer.translator.tasks import cel
import sys

# Run all the queues in one
cel.worker_main(sys.argv + ['--beat'])
