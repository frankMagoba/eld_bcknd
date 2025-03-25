"""
WSGI config for eld_log project.

This module redirects to the actual WSGI application in the eld_log package.
"""

import os
import sys

# Add the project directory to the Python path
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.append(path)

# Import the WSGI application from the actual location
from eld_log.eld_log.wsgi import application 