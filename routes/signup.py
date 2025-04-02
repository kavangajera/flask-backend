# routes/signup.py
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from models.customer import Customer
from extensions import db

signup_bp = Blueprint('signup', __name__)

@signup_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()

        # Validate data
        if not data or not all(key in data for key in ['name', 'email', 'mobile', 'password']):
            return jsonify({'message': 'All fields are required'}), 400

        # Check for duplicate email or mobile
        if Customer.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'Email already registered'}), 400

        if Customer.query.filter_by(mobile=data['mobile']).first():
            return jsonify({'message': 'Mobile number already registered'}), 400

        # Create and save customer
        new_customer = Customer(
            name=data['name'],
            email=data['email'],
            mobile=data['mobile'],
            password=generate_password_hash(data['password']),
            role='customer'  # Default role
        )
        db.session.add(new_customer)
        db.session.commit()

        return jsonify({'message': 'Registration successful!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 400