#!/usr/bin/env bash
# exit on error
set -o errexit

# install dependencies
pip install -r requirements.txt

# create static directory if it doesn't exist
mkdir -p staticfiles

# make a symlink for wsgi.py if it doesn't exist at the root
if [ ! -f ../wsgi.py ]; then
  echo "Creating symlink for wsgi.py"
  ln -sf eld_log/wsgi.py ../wsgi.py
fi

# collect static files
python manage.py collectstatic --no-input

# apply migrations
python manage.py migrate 