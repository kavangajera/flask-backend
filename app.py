# # app.py
# from flask import Flask, jsonify
# from flask_cors import CORS
# from datetime import timedelta
# from extensions import db
# from routes.signup import signup_bp
# from routes.login import login_bp
# from routes.products import products_bp
# from routes.order import order_bp
# from routes.admin_signup import admin_signup_bp
# # Import models
# from models.customer import Customer
# from models.product import Product, ProductImage
# from models.order import OrderHistory, OrderHistoryItem

# import os
# import secrets

# # Initialize Flask app
# app = Flask(__name__)



# # Generate a secure secret key
# app.config['SECRET_KEY'] = secrets.token_hex(32)

# # Remove session-related configurations
# # Remove Flask-Session initialization

# # Enable CORS with enhanced security
# cors = CORS(app, resources={
#     r"/*": {
#         "origins": "http://mtm-store.com",
#         "allow_headers": ["Content-Type", "Authorization"],
#         "supports_credentials": True,
#         "expose_headers": ["Authorization"]
#     }
# })

# # Configure MySQL database
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mtm_user:Pass%402025%23@103.198.175.81/mtm_store_db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# # Security configurations
# app.config['JWT_SECRET_KEY'] = secrets.token_hex(32)
# app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

# # Initialize extensions
# db.init_app(app)

# # Register blueprints
# app.register_blueprint(signup_bp)
# app.register_blueprint(login_bp)
# app.register_blueprint(products_bp)
# app.register_blueprint(order_bp)
# app.register_blueprint(admin_signup_bp)

# @app.after_request
# def add_security_headers(response):
#     """Add additional security headers"""
#     response.headers['X-Content-Type-Options'] = 'nosniff'
#     response.headers['X-Frame-Options'] = 'SAMEORIGIN'
#     response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
#     # CORS headers
#     response.headers["Access-Control-Allow-Origin"] = "http://mtm-store.com"
#     response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
#     response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
#     response.headers["Access-Control-Allow-Credentials"] = "true"
    
#     return response

# @app.errorhandler(401)
# def unauthorized(error):
#     return jsonify({
#         'message': 'Unauthorized access',
#         'status': 'error'
#     }), 401

# if __name__ == '__main__':
#     # Ensure database tables are created
#     with app.app_context():
#         db.create_all()
    
#     # Run the app
#     app.run(host='0.0.0.0', port=5005, debug=True)

from flask import Flask, jsonify
from flask_cors import CORS
from datetime import timedelta
from extensions import db
from routes.signup import signup_bp
from routes.login import login_bp, setup_google_oauth
from routes.products import products_bp
from routes.order import order_bp
from routes.admin_signup import admin_signup_bp
from routes.wishlist import wishlist_bp
from routes.state import state_bp
from routes.address import address_bp
from routes.profile import profile_bp
# Import models
from models.customer import Customer
from models.product import Product, ProductImage
from models.order import OrderHistory, OrderHistoryItem
from models.cart import Cart, CartItem

from dotenv import load_dotenv
import os
import secrets

# Initialize Flask app
app = Flask(__name__)
load_dotenv()

client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
# Generate a secure secret key
# app.config['SECRET_KEY'] = secrets.token_hex(32)

app.config['SECRET_KEY'] = "shrivarajunizationfaranfusion"

# Google OAuth configuration
app.config['GOOGLE_CLIENT_ID'] = client_id  # Replace with your Google Client ID
app.config['GOOGLE_CLIENT_SECRET'] = client_secret # Replace with your Google Client Secret

# Enable CORS with enhanced security
cors = CORS(app, resources={
    r"/*": {
        "origins": "http://mtm-store.com",
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "expose_headers": ["Authorization"]
    }
})

# Configure MySQL database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mtm_user:Pass%402025%23@103.198.175.81/mtm_store_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Security configurations
app.config['JWT_SECRET_KEY'] = secrets.token_hex(32)
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

# Initialize extensions
db.init_app(app)

# Initialize Google OAuth
setup_google_oauth(app)

# Register blueprints
app.register_blueprint(signup_bp)
app.register_blueprint(login_bp)
app.register_blueprint(products_bp)
app.register_blueprint(order_bp)
app.register_blueprint(admin_signup_bp)
app.register_blueprint(wishlist_bp)
app.register_blueprint(state_bp)
app.register_blueprint(address_bp)
app.register_blueprint(profile_bp)



@app.after_request
def add_security_headers(response):
    """Add additional security headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # CORS headers
    response.headers["Access-Control-Allow-Origin"] = "http://mtm-store.com"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'message': 'Unauthorized access',
        'status': 'error'
    }), 401

if __name__ == '__main__':
    # Ensure database tables are created
    with app.app_context():
        db.create_all()
    
    # Run the app
    app.run(host='0.0.0.0', port=5005, debug=True)