# import logging
# import jwt
# from datetime import datetime, timedelta
# from flask import Blueprint, request, jsonify, current_app
# from werkzeug.security import check_password_hash
# from models.customer import Customer
# from extensions import db
# from middlewares.auth import token_required

# # Configure logging
# logging.basicConfig(level=logging.INFO, 
#                     format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# login_bp = Blueprint('login', __name__)

# # Maintain a blacklist of invalidated tokens (you might want to use Redis in production)
# token_blacklist = set()

# @login_bp.route('/login', methods=['POST'])
# def login():
#     try:
#         # Log incoming request details
#         logger.debug(f"Login attempt - Request data: {request.get_json()}")
        
#         # Validate request data
#         data = request.get_json()

#         if not data:
#             logger.warning("Login attempt with empty request body")
#             return jsonify({
#                 'message': 'Request body is empty'
#             }), 400

#         # Check for required fields
#         required_fields = ['email', 'password']
#         for field in required_fields:
#             if field not in data or not data[field]:
#                 logger.warning(f"Login attempt with missing {field}")
#                 return jsonify({'message': f'{field.capitalize()} is required'}), 400

#         # Find customer by email
#         customer = Customer.query.filter_by(email=data['email']).first()

#         # Validate credentials
#         if not customer:
#             logger.info(f"Login attempt with non-existent email: {data['email']}")
#             return jsonify({'message': 'Invalid email or password'}), 401

#         # Check password
#         if not check_password_hash(customer.password, data['password']):
#             logger.warning(f"Failed login attempt for email: {data['email']}")
#             return jsonify({'message': 'Invalid email or password'}), 401

#         # Generate JWT token
#         secret_key = current_app.config['SECRET_KEY']
#         payload = {
#             'customer_id': customer.customer_id,
#             'email': customer.email,
#             'role': customer.role,
#             'exp': datetime.now(tz=ZoneInfo('Asia/Kolkata'))() + timedelta(days=1)  # Token expires in 1 day
#         }
#         token = jwt.encode(payload, secret_key, algorithm='HS256')

#         # Log successful login
#         logger.info(f"Successful login for user: {customer.email}")

#         # Prepare response data
#         response_data = {
#             'message': 'Login successful!',
#             'token': token,
#             'user': {
#                 'customer_id': customer.customer_id,
#                 'name': customer.name,
#                 'email': customer.email,
#                 'mobile': customer.mobile,
#                 'role': customer.role
#             }
#         }

#         return jsonify(response_data), 200

#     except Exception as e:
#         logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
#         return jsonify({
#             'message': 'An unexpected error occurred',
#             'error_details': str(e)
#         }), 500

# @login_bp.route('/logout', methods=['POST'])
# @token_required()
# def logout():
#     """
#     Logout route that invalidates the current token
#     Requires a valid JWT token in the Authorization header
#     """
#     try:
#         # Extract token from Authorization header
#         auth_header = request.headers.get('Authorization')
#         if not auth_header or not auth_header.startswith('Bearer '):
#             return jsonify({'message': 'Invalid token'}), 401

#         token = auth_header.split(' ')[1]

#         # Add token to blacklist
#         token_blacklist.add(token)

#         # Log logout
#         logger.info(f"Logout for user: {request.current_user.email}")

#         return jsonify({
#             'message': 'Logged out successfully'
#         }), 200

#     except Exception as e:
#         logger.error(f"Unexpected error during logout: {str(e)}")
#         return jsonify({
#             'message': 'An error occurred during logout',
#             'error': str(e)
#         }), 500

# @login_bp.route('/check-auth', methods=['GET'])
# def check_authentication():
#     """
#     Route to check current authentication status
#     Can be used by frontend to verify user's login state
#     """
#     try:
#         # Get token from Authorization header
#         auth_header = request.headers.get('Authorization')
#         if not auth_header or not auth_header.startswith('Bearer '):
#             return jsonify({
#                 'is_authenticated': False,
#                 'user': None
#             }), 200

#         token = auth_header.split(' ')[1]
        
#         # Check if token is blacklisted
#         if token in token_blacklist:
#             return jsonify({
#                 'is_authenticated': False,
#                 'user': None
#             }), 200
        
#         # Verify token
#         try:
#             secret_key = current_app.config['SECRET_KEY']
#             payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
#             # Find customer
#             customer = Customer.query.get(payload['customer_id'])
#             if not customer:
#                 return jsonify({
#                     'is_authenticated': False,
#                     'user': None
#                 }), 200

#             return jsonify({
#                 'is_authenticated': True,
#                 'user': {
#                     'customer_id': customer.customer_id,
#                     'name': customer.name,
#                     'email': customer.email,
#                     'role': customer.role
#                 }
#             }), 200

#         except jwt.ExpiredSignatureError:
#             return jsonify({
#                 'is_authenticated': False,
#                 'user': None
#             }), 200
#         except jwt.InvalidTokenError:
#             return jsonify({
#                 'is_authenticated': False,
#                 'user': None
#             }), 200

#     except Exception as e:
#         logger.error(f"Error in authentication check: {str(e)}")
#         return jsonify({'message': 'An error occurred'}), 500











import logging
import jwt
import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
from models.customer import Customer
from extensions import db
from middlewares.auth import token_required
from authlib.integrations.flask_client import OAuth
from zoneinfo import ZoneInfo

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

login_bp = Blueprint('login', __name__)

# Initialize OAuth
oauth = OAuth()

# Maintain a blacklist of invalidated tokens (you might want to use Redis in production)
token_blacklist = set()

def setup_google_oauth(app):
    """
    Configure Google OAuth with the Flask app
    Call this function from app.py after creating the app
    """
    oauth.init_app(app)
    
    # Google OAuth config
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

@login_bp.route('/login/google')
def login_google():
    """
    Initiate Google OAuth2 authentication flow
    """
    redirect_uri = 'https://mtm-store.com/api/login/google/callback'
    return oauth.google.authorize_redirect(redirect_uri)

@login_bp.route('/login/google/callback')
def google_auth_callback():
    """
    Handle Google OAuth2 callback
    """
    try:
        # Complete the OAuth flow
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.parse_id_token(token, nonce=session.get("nonce"))

        
        # Get user info
        google_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name')
        
        # Check if this Google account is already registered
        customer = Customer.query.filter_by(google_id=google_id).first()
        
        if not customer:
            # Check if a user with this email exists
            email_customer = Customer.query.filter_by(email=email).first()
            
            if email_customer:
                # Link existing account with Google ID
                email_customer.google_id = google_id
                db.session.commit()
                customer = email_customer
            else:
                # Create a new user with Google info
                # Generate a random password (user won't use it)
                random_password = generate_password_hash(os.urandom(24).hex())
                
                customer = Customer(
                    name=name,
                    email=email,
                    password=random_password,
                    google_id=google_id,
                    role='customer'
                )
                db.session.add(customer)
                db.session.commit()
                
                logger.info(f"New user created via Google Auth: {email}")
        
        # Generate JWT token
        secret_key = current_app.config['SECRET_KEY']
        payload = {
            'customer_id': customer.customer_id,
            'email': customer.email,
            'role': customer.role,
            'exp': datetime.now(tz=ZoneInfo('Asia/Kolkata')) + timedelta(days=1)  # Token expires in 1 day
        }
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        # Log successful login
        logger.info(f"Successful Google login for user: {customer.email}")
        
        # In a real application, you'd redirect to your frontend with the token
        # For demonstration, returning a JSON response
        response_data = {
            'message': 'Google login successful!',
            'token': token,
            'user': {
                'customer_id': customer.customer_id,
                'name': customer.name,
                'email': customer.email,
                'mobile': customer.mobile,
                'role': customer.role
            }
        }
        
        # Normally you would redirect to your frontend with the token
        redirect_url = f"https://mtm-store.com/auth-callback?token={token}&user={json.dumps(response_data['user'])}"
        return redirect(redirect_url)
        
    except Exception as e:
        logger.error(f"Error during Google authentication: {str(e)}", exc_info=True)
        return jsonify({
            'message': 'Google authentication failed',
            'error_details': str(e)
        }), 500

@login_bp.route('/login', methods=['POST'])
def login():
    try:
        # Log incoming request details
        logger.debug(f"Login attempt - Request data: {request.get_json()}")
        
        # Validate request data
        data = request.get_json()

        if not data:
            logger.warning("Login attempt with empty request body")
            return jsonify({
                'message': 'Request body is empty'
            }), 400

        # Check for required fields
        required_fields = ['email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                logger.warning(f"Login attempt with missing {field}")
                return jsonify({'message': f'{field.capitalize()} is required'}), 400

        # Find customer by email
        customer = Customer.query.filter_by(email=data['email']).first()

        # Validate credentials
        if not customer:
            logger.info(f"Login attempt with non-existent email: {data['email']}")
            return jsonify({'message': 'Invalid email or password'}), 401

        # Check password
        if not check_password_hash(customer.password, data['password']):
            logger.warning(f"Failed login attempt for email: {data['email']}")
            return jsonify({'message': 'Invalid email or password'}), 401

        # Generate JWT token
        secret_key = current_app.config['SECRET_KEY']
        payload = {
            'customer_id': customer.customer_id,
            'email': customer.email,
            'role': customer.role,
            'exp': datetime.now(tz=ZoneInfo('Asia/Kolkata')) + timedelta(days=1)  # Token expires in 1 day
        }
        token = jwt.encode(payload, secret_key, algorithm='HS256')

        # Log successful login
        logger.info(f"Successful login for user: {customer.email}")

        # Prepare response data
        response_data = {
            'message': 'Login successful!',
            'token': token,
            'user': {
                'customer_id': customer.customer_id,
                'name': customer.name,
                'email': customer.email,
                'mobile': customer.mobile,
                'role': customer.role
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        return jsonify({
            'message': 'An unexpected error occurred',
            'error_details': str(e)
        }), 500

@login_bp.route('/logout', methods=['POST'])
@token_required()
def logout():
    """
    Logout route that invalidates the current token
    Requires a valid JWT token in the Authorization header
    """
    try:
        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': 'Invalid token'}), 401

        token = auth_header.split(' ')[1]

        # Add token to blacklist
        token_blacklist.add(token)

        # Log logout
        logger.info(f"Logout for user: {request.current_user.email}")

        return jsonify({
            'message': 'Logged out successfully'
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error during logout: {str(e)}")
        return jsonify({
            'message': 'An error occurred during logout',
            'error': str(e)
        }), 500

@login_bp.route('/check-auth', methods=['GET'])
def check_authentication():
    """
    Route to check current authentication status
    Can be used by frontend to verify user's login state
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'is_authenticated': False,
                'user': None
            }), 200

        token = auth_header.split(' ')[1]
        
        # Check if token is blacklisted
        if token in token_blacklist:
            return jsonify({
                'is_authenticated': False,
                'user': None
            }), 200
        
        # Verify token
        try:
            secret_key = current_app.config['SECRET_KEY']
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Find customer
            customer = Customer.query.get(payload['customer_id'])
            if not customer:
                return jsonify({
                    'is_authenticated': False,
                    'user': None
                }), 200

            return jsonify({
                'is_authenticated': True,
                'user': {
                    'customer_id': customer.customer_id,
                    'name': customer.name,
                    'email': customer.email,
                    'role': customer.role
                }
            }), 200

        except jwt.ExpiredSignatureError:
            return jsonify({
                'is_authenticated': False,
                'user': None
            }), 200
        except jwt.InvalidTokenError:
            return jsonify({
                'is_authenticated': False,
                'user': None
            }), 200

    except Exception as e:
        logger.error(f"Error in authentication check: {str(e)}")
        return jsonify({'message': 'An error occurred'}), 500
