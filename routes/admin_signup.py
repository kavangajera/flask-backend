import os
import jwt
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash
from models.customer import Customer
from extensions import db

admin_signup_bp = Blueprint('admin_signup', __name__)

# Load the admin registration token from environment variable
ADMIN_REGISTRATION_TOKEN = os.getenv('ADMIN_REGISTRATION_TOKEN', 'default-admin-token')

@admin_signup_bp.route('/admin-signup', methods=['POST'])
def admin_signup():
    try:
        data = request.get_json()
        
        # Validate that all required fields are present
        if not data or not all(key in data for key in ['name', 'email', 'mobile', 'password', 'admin_token']):
            return jsonify({'message': 'All fields are required'}), 400
        
        # Check admin registration token
        if data['admin_token'] != ADMIN_REGISTRATION_TOKEN:
            return jsonify({'message': 'Invalid admin registration token'}), 403
        
        # Check for duplicate email or mobile
        if Customer.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'Email already registered'}), 400

        if Customer.query.filter_by(mobile=data['mobile']).first():
            return jsonify({'message': 'Mobile number already registered'}), 400

        # Create and save admin customer
        new_admin = Customer(
            name=data['name'],
            email=data['email'],
            mobile=data['mobile'],
            password=generate_password_hash(data['password']),
            role='admin'  # Set role to admin
        )
        db.session.add(new_admin)
        db.session.commit()

        # Generate JWT token
        secret_key = current_app.config['SECRET_KEY']
        payload = {
            'customer_id': new_admin.customer_id,
            'email': new_admin.email,
            'role': new_admin.role,
            'exp': datetime.utcnow() + timedelta(days=1)  # Token expires in 1 day
        }
        token = jwt.encode(payload, secret_key, algorithm='HS256')

        # Prepare response
        response_data = {
            'message': 'Admin registration successful!',
            'token': token,
            'admin': {
                'customer_id': new_admin.customer_id,
                'name': new_admin.name,
                'email': new_admin.email,
                'mobile': new_admin.mobile,
                'role': new_admin.role
            }
        }

        return jsonify(response_data), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'message': 'Admin registration failed', 
            'error': str(e)
        }), 400