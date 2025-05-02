#!/usr/bin/env python3
import sys
import logging
import site

# Enable detailed logging to Apache error log
logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logging.debug('Starting Flask application via WSGI')

# Add the virtual environment's site-packages to the Python path
site.addsitedir('/var/www/flask-backend/venv/lib/python3.10/site-packages')

# Add your Flask app directory to the Python path
sys.path.insert(0, '/var/www/flask-backend')

try:
    # Import your Flask app - make sure 'app' matches the Flask instance name in app.py
    from app import app as application
    logging.debug('Flask application imported successfully')
except Exception as e:
    logging.error(f'Failed to import Flask application: {str(e)}')
    raise

# Log application routes for debugging
logging.debug('Available routes:')
for rule in application.url_map.iter_rules():
    logging.debug(f'Route: {rule.rule}, Methods: {rule.methods}')
