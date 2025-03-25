#!/usr/bin/env bash
# exit on error
set -o errexit

# Print debugging information
echo "Starting build process..."
echo "Current directory: $(pwd)"

# install dependencies
pip install -r requirements.txt

# create static directory if it doesn't exist
mkdir -p staticfiles

# Show database information (without revealing credentials)
echo "Database configuration check:"
python -c "import os; from django.conf import settings; print(f'DATABASE ENGINE: {settings.DATABASES[\"default\"][\"ENGINE\"]}'); print(f'DATABASE NAME: {settings.DATABASES[\"default\"][\"NAME\"]}'); print(f'DATABASE HOST: {settings.DATABASES[\"default\"][\"HOST\"]}')" || echo "Failed to check database configuration"

# Make migrations to be safe (shouldn't create new ones but will verify models)
echo "Making migrations..."
python manage.py makemigrations

# Show migration plan
echo "Migration plan:"
python manage.py showmigrations

# apply migrations
echo "Applying migrations..."
python manage.py migrate --noinput

# Verify table creation
echo "Verifying tables:"
python -c "import os; from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT table_name FROM information_schema.tables WHERE table_schema = \'public\';'); tables = cursor.fetchall(); print('Tables found:', tables)" || echo "Failed to verify tables"

# collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input 