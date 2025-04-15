from flask import Blueprint, request, jsonify
from models.offline_customer import OfflineCustomer
from models.address import Address
from extensions import db
from flask_login import login_required, current_user
from middlewares.auth import token_required

offline_customer_bp = Blueprint('offline_customer', __name__)

# Create
@offline_customer_bp.route('/offline-customers', methods=['POST'])
@token_required(roles=['admin'])
def create_offline_customer():
    
        
    data = request.get_json()
    
    # Create customer
    new_customer = OfflineCustomer(
        name=data['name'],
        mobile=data.get('mobile'),
        email=data['email'],
       
    )
    
    db.session.add(new_customer)
    db.session.flush()  # Get the customer_id before commit
    
    # Add address if provided
    if 'address' in data:
        address_data = data['address']
        new_address = Address(
            offline_customer_id=new_customer.customer_id,
            street=address_data['street'],
            city=address_data['city'],
            state=address_data['state'],
            pincode=address_data['pincode'],
            is_default=address_data.get('is_default', True)  # First address is default by default
        )
        db.session.add(new_address)
    
    db.session.commit()
    
    # Get the complete customer data with address
    customer_dict = new_customer.get_dict()
    if 'address' in data:
        customer_dict['address'] = {
            'address_id': new_address.address_id,
            'street': new_address.street,
            'city': new_address.city,
            'state': new_address.state,
            'pincode': new_address.pincode,
            'is_default': new_address.is_default
        }
    
    return jsonify(customer_dict), 201

# Read (Get all)
@offline_customer_bp.route('/offline-customers', methods=['GET'])
@token_required(roles=['admin'])
def get_offline_customers():
    customers = OfflineCustomer.query.all()
    result = []
    for customer in customers:
        customer_data = customer.get_dict()
        addresses = [{
            'address_id': addr.address_id,
            'street': addr.street,
            'city': addr.city,
            'state': addr.state,
            'pincode': addr.pincode,
            'is_default': addr.is_default
        } for addr in customer.addresses]
        customer_data['addresses'] = addresses
        result.append(customer_data)
    return jsonify(result)
# Read (Get one)
@offline_customer_bp.route('/offline-customers/<int:customer_id>', methods=['GET'])
@token_required(roles=['admin'])
def get_offline_customer(customer_id):
    
        
    customer = OfflineCustomer.query.get_or_404(customer_id)
    customer_data = {
        'customer_id': customer.customer_id,
        'name': customer.name,
        'mobile': customer.mobile,
        'email': customer.email,
        'role': customer.role,
        'google_id': customer.google_id
    }
   
    addresses = [{
        'address_id': addr.address_id,
        'street': addr.street,
        'city': addr.city,
        'state': addr.state,
        'pincode': addr.pincode,
        'is_default': addr.is_default
    } for addr in customer.addresses]
    customer_data['addresses'] = addresses
    return jsonify(customer_data)

# Update
@offline_customer_bp.route('/offline-customers/<int:customer_id>', methods=['PUT'])
@token_required(roles=['admin'])
def update_offline_customer(customer_id):
    
        
    customer = OfflineCustomer.query.get_or_404(customer_id)
    data = request.get_json()
    
    customer.name = data.get('name', customer.name)
    customer.mobile = data.get('mobile', customer.mobile)
    customer.email = data.get('email', customer.email)
    customer.age = data.get('age', customer.age)
    customer.gender = data.get('gender', customer.gender)
    
    if 'password' in data:
        customer.password = data['password']
    
    db.session.commit()
    return jsonify(customer.get_dict())

# Delete
@offline_customer_bp.route('/offline-customers/<int:customer_id>', methods=['DELETE'])
@token_required(roles=['admin'])
def delete_offline_customer(customer_id):
    
        
    customer = OfflineCustomer.query.get_or_404(customer_id)
    db.session.delete(customer)
    db.session.commit()
    return jsonify({'message': 'Customer deleted successfully'})

# Add Address
@offline_customer_bp.route('/offline-customers/<int:customer_id>/addresses', methods=['POST'])
@token_required(roles=['admin'])
def add_offline_customer_address(customer_id):
    
        
    customer = OfflineCustomer.query.get_or_404(customer_id)
    data = request.get_json()
    
    new_address = Address(
        offline_customer_id=customer.customer_id,
        street=data['street'],
        city=data['city'],
        state=data['state'],
        pincode=data['pincode'],
        is_default=data.get('is_default', False)
    )
    
    db.session.add(new_address)
    db.session.commit()
    return jsonify({
        'message': 'Address added successfully',
        'address_id': new_address.address_id
    }), 201

# Get Customer Addresses
@offline_customer_bp.route('/offline-customers/<int:customer_id>/addresses', methods=['GET'])
@token_required(roles=['admin'])
def get_offline_customer_addresses(customer_id):
    
        
    customer = OfflineCustomer.query.get_or_404(customer_id)
    addresses = Address.query.filter_by(offline_customer_id=customer.customer_id).all()
    
    return jsonify([{
        'address_id': addr.address_id,
        'street': addr.street,
        'city': addr.city,
        'state': addr.state,
        'pincode': addr.pincode,
        'is_default': addr.is_default
    } for addr in addresses]) 