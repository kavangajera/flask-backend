# middlewares/auth.py
import jwt
from functools import wraps
from flask import request, jsonify, current_app
from models.customer import Customer

# Import the token blacklist from login routes


def token_required(roles=None):
    from routes.login import token_blacklist
    """
    Decorator to require JWT token authentication
    
    :param roles: Optional list of roles allowed to access the route
    :return: Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if Authorization header is present
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({
                    'message': 'Authentication token is missing',
                    'status': 'error'
                }), 401

            try:
                # Extract token (expecting "Bearer {token}")
                if not auth_header.startswith('Bearer '):
                    return jsonify({
                        'message': 'Invalid token format',
                        'status': 'error'
                    }), 401

                token = auth_header.split(' ')[1]

                # Check if token is blacklisted
                if token in token_blacklist:
                    return jsonify({
                        'message': 'Token is no longer valid',
                        'status': 'error'
                    }), 401

                # Decode the token
                secret_key = current_app.config['SECRET_KEY']
                payload = jwt.decode(token, secret_key, algorithms=['HS256'])

                # Find the customer
                customer = Customer.query.get(payload['customer_id'])
                if not customer:
                    return jsonify({
                        'message': 'Invalid token',
                        'status': 'error'
                    }), 401

                # Check role if specified
                if roles and customer.role not in roles:
                    return jsonify({
                        'message': 'Insufficient permissions',
                        'status': 'error'
                    }), 403

                # Attach customer to the request for use in route
                request.current_user = customer

                return f(*args, **kwargs)

            except jwt.ExpiredSignatureError:
                return jsonify({
                    'message': 'Token has expired',
                    'status': 'error'
                }), 401
            except jwt.InvalidTokenError:
                return jsonify({
                    'message': 'Invalid token',
                    'status': 'error'
                }), 401

        return decorated_function
    return decorator