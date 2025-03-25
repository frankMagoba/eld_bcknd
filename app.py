"""
This file exposes the WSGI application for Render deployment.
"""

import os
import sys

# Add the current directory to the path
current_path = os.path.dirname(os.path.abspath(__file__))
if current_path not in sys.path:
    sys.path.insert(0, current_path)

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eld_log.settings')

# Import the WSGI application
from django.core.wsgi import get_wsgi_application
app = application = get_wsgi_application() 