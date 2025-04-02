import sys
import logging

# Log errors to Apache error log
logging.basicConfig(stream=sys.stderr)

# Add your application directory to the Python path
sys.path.insert(0, '/home/mtmstore/Downloads/ecommerce-main/ecom-project-main')

# Import your Flask app - make sure this matches your actual app variable name
from app import app as application
import sys
import logging

# Add your application directory to the Python path
sys.path.insert(0, '/home/mtmstore/Downloads/ecommerce-main/ecom-project-main')

# Import your Flask app
from app import app as application
#!/usr/bin/python3
import sys
import logging
import site

# Log errors
logging.basicConfig(stream=sys.stderr)

# Add the virtual environment site-packages to the path
site.addsitedir('/var/www/flask-backend/venv/lib/python3.10/site-packages')

# Add application directory to path
sys.path.insert(0, '/var/www/flask-backend')

# Import your Flask app
from app import app as application
