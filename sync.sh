#!/bin/bash
cd $(dirname $0)
. .venv/bin/activate
python ./ical_to_gcal_sync.py
