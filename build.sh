#!/usr/bin/env bash
# exit on error
set -o errexit

# install dependencies
pip install -r requirements.txt

# create static directory if it doesn't exist
mkdir -p staticfiles

# collect static files
python manage.py collectstatic --no-input

# apply migrations
python manage.py migrate 