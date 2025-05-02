from flask import Blueprint, current_app, request, jsonify
from middlewares.auth import token_required
from extensions import db
from models.customer import Customer
import requests


profile_bp = Blueprint('profile',__name__)

@profile_bp.route('/profile-info',methods=['GET'])
@token_required(roles=['customer','admin'])
def get_profile_info():
    current_user = request.current_user
    profile = Customer.query.filter_by(customer_id=current_user.customer_id).first()
    return jsonify({
        'success' : True,
        'profile-info': profile.get_dict()
    })

@profile_bp.route('/profile', methods=['PUT'])
@token_required(roles=['customer', 'admin'])
def update_profile():
    """Update all customer profile fields at once"""
    current_user = request.current_user
    data = request.json
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    # Get the customer from the database
    customer = Customer.query.filter_by(customer_id=current_user.customer_id).first()
    
    # Only update fields that are allowed to be updated
    if 'name' in data:
        customer.name = data['name']
    if 'age' in data:
        customer.age = data['age']
    if 'gender' in data:
        customer.gender = data['gender']
    if 'mobile' in data:
        # Check if mobile number already exists
        existing_mobile = Customer.query.filter_by(mobile=data['mobile']).first()
        if existing_mobile and existing_mobile.customer_id != customer.customer_id:
            return jsonify({
                'success': False,
                'message': 'Mobile number already in use'
            }), 400
        customer.mobile = data['mobile']
    if 'email' in data and not customer.is_google_user():
        # Check if email already exists
        existing_email = Customer.query.filter_by(email=data['email']).first()
        if existing_email and existing_email.customer_id != customer.customer_id:
            return jsonify({
                'success': False,
                'message': 'Email already in use'
            }), 400
        customer.email = data['email']
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'profile-info': customer.get_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating profile: {str(e)}'
        }), 500

@profile_bp.route('/profile/<field>', methods=['PATCH'])
@token_required(roles=['customer', 'admin'])
def update_profile_field(field):
    """Update a single field of the customer profile"""
    current_user = request.current_user
    data = request.json
    
    if not data or field not in data:
        return jsonify({
            'success': False,
            'message': f'No {field} provided'
        }), 400
    
    # Get the customer from the database
    customer = Customer.query.filter_by(customer_id=current_user.customer_id).first()
    
    # Handle specific field updates
    if field == 'name':
        customer.name = data['name']
    elif field == 'age':
        customer.age = data['age']
    elif field == 'gender':
        customer.gender = data['gender']
    elif field == 'mobile':
        # Check if mobile number already exists
        existing_mobile = Customer.query.filter_by(mobile=data['mobile']).first()
        if existing_mobile and existing_mobile.customer_id != customer.customer_id:
            return jsonify({
                'success': False,
                'message': 'Mobile number already in use'
            }), 400
        customer.mobile = data['mobile']
    elif field == 'email' and not customer.is_google_user():
        # Check if email already exists
        existing_email = Customer.query.filter_by(email=data['email']).first()
        if existing_email and existing_email.customer_id != customer.customer_id:
            return jsonify({
                'success': False,
                'message': 'Email already in use'
            }), 400
        customer.email = data['email']
    else:
        return jsonify({
            'success': False,
            'message': f'Field {field} cannot be updated or does not exist'
        }), 400
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'{field} updated successfully',
            'profile-info': customer.get_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating {field}: {str(e)}'
        }), 500

@profile_bp.route('/password', methods=['PUT'])
@token_required(roles=['customer', 'admin'])
def update_password():
    """Update customer password"""
    current_user = request.current_user
    data = request.json
    
    if not data or 'current_password' not in data or 'new_password' not in data:
        return jsonify({
            'success': False,
            'message': 'Current password and new password are required'
        }), 400
    
    # Get the customer from the database
    customer = Customer.query.filter_by(customer_id=current_user.customer_id).first()
    
    # Don't allow password change for Google users
    if customer.is_google_user():
        return jsonify({
            'success': False,
            'message': 'Google users cannot change password'
        }), 400
    
    # Verify current password (assuming passwords are hashed)
    # You'll need to implement proper password verification based on your hashing method
    from werkzeug.security import check_password_hash, generate_password_hash
    
    if not check_password_hash(customer.password, data['current_password']):
        return jsonify({
            'success': False,
            'message': 'Current password is incorrect'
        }), 401
    
    # Update password with new hashed password
    customer.password = generate_password_hash(data['new_password'])
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Password updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating password: {str(e)}'
        }), 500