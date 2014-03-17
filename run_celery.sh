#!/bin/bash

celery -A appcomposer.composers.translate.tasks worker
