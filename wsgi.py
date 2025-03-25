"""
WSGI config for eld_log project.

This module contains the WSGI application for Render deployment.
"""

import os
import sys

# Add the parent directory to the Python path
current_path = os.path.dirname(os.path.abspath(__file__))
# Make sure the current directory is in the path
if current_path not in sys.path:
    sys.path.insert(0, current_path)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eld_log.settings')

# Import Django's WSGI handler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application() 