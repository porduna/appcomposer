#!/bin/bash
celery -A appcomposer.translator.tasks beat
