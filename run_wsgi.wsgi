#!/usr/bin/env python

import os
import sys

sys.stdout = sys.stderr

APPCOMPOSER_DIR = os.path.dirname(__file__)

sys.path.insert(0, APPCOMPOSER_DIR)
os.chdir(APPCOMPOSER_DIR)

import config

from appcomposer import app as application
application.config.from_object('config')
