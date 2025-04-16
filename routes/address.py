from flask import Blueprint, current_app, request, jsonify
from middlewares.auth import token_required
from extensions import db
from models.address import Address
from models.state import State
import json
import requests

address_bp = Blueprint('address', __name__)

@address_bp.route('/addresses', methods=['GET'])
@token_required(roles=['customer'])
def get_addresses():
    """Get all addresses for the current user"""
    current_user = request.current_user
    addresses = Address.query.filter_by(customer_id=current_user.customer_id).all()
    return jsonify({
        'success': True,
        'addresses': [address.to_dict() for address in addresses]
    })

@address_bp.route('/addresses/<int:address_id>', methods=['GET'])
@token_required(roles=['customer'])
def get_address(address_id):
    """Get a specific address by ID"""
    current_user = request.current_user
    address = Address.query.filter_by(address_id=address_id, customer_id=current_user.customer_id).first()
    
    if not address:
        return jsonify({
            'success': False,
            'message': 'Address not found'
        }), 404
    
    return jsonify({
        'success': True,
        'address': address.to_dict()
    })




def is_service_available(pincode):
    """
    Check if delivery service is available for the given pincode using Delhivery API
    
    Args:
        pincode (str): The pincode to check
        
    Returns:
        dict: A dictionary with success status and message
    """
    import requests
    
    if not pincode:
        return {
            'success': False,
            'message': 'Pincode is required'
        }
    
    url = f"https://track.delhivery.com/c/api/pin-codes/json/?filter_codes={pincode}"
    
    try:
        response = requests.get(
            url,
            headers={
                'Authorization': 'e3e340a4a9415a5282e8df1995fef1ceb82062cf',
                'Content-Type': 'application/json'
            }
        )
        
        if not response.ok:
            return {
                'success': False,
                'message': f'Failed to check pincode serviceability: {response.reason}'
            }
        
        data = response.json()
        
        # Check if delivery_codes array is empty
        if not data.get('delivery_codes'):
            return {
                'success': False,
                'message': f'Delivery is not available for pincode {pincode}'
            }
        
        pincode_data = data['delivery_codes'][0].get('postal_code')
        
        if not pincode_data:
            return {
                'success': False,
                'message': f'Invalid or unsupported pincode {pincode}'
            }
        
        is_prepaid = pincode_data.get('pre_paid') == 'Y'
        is_cod = pincode_data.get('cod') == 'Y'
        
        if is_prepaid or is_cod:
            return {
                'success': True,
                'message': f'Pincode {pincode} is serviceable',
                'data': {
                    'prepaid': is_prepaid,
                    'cod': is_cod,
                    'city': pincode_data.get('city'),
                    'state_code': pincode_data.get('state_code')
                }
            }
        else:
            return {
                'success': False,
                'message': f'Delivery is not available for pincode {pincode}'
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Error checking pincode serviceability: {str(e)}'
        }



@address_bp.route('/add-address', methods=['POST'])
@token_required(roles=['customer'])
def add_address():
    """Add a new address for the current user"""
    data = request.json
    current_user = request.current_user
    
    # Basic validation
    required_fields = ['name', 'mobile', 'pincode', 'locality', 'address_line', 'city', 'state_id', 'address_type']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({
                'success': False,
                'message': f'Missing required field: {field}'
            }), 400
    
    # Validate state_id exists
    state = State.query.get(data['state_id'])
    if not state:
        return jsonify({
            'success': False,
            'message': 'Invalid state selected'
        }), 400
    
    # Check if pincode is serviceable
    service_check = is_service_available(data['pincode'])
    if not service_check['success']:
        return jsonify(service_check), 400
    
    # Handle "Use my current location" if latitude and longitude are provided
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    new_address = Address(
        customer_id=current_user.customer_id,
        name=data['name'],
        mobile=data['mobile'],
        pincode=data['pincode'],
        locality=data['locality'],
        address_line=data['address_line'],
        city=data['city'],
        state_id=data['state_id'],
        landmark=data.get('landmark'),
        alternate_phone=data.get('alternate_phone'),
        address_type=data['address_type'],
        latitude=latitude,
        longitude=longitude
    )
    
    db.session.add(new_address)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Address added successfully',
        'address': new_address.to_dict()
    }), 201

@address_bp.route('/addresses/<int:address_id>', methods=['PUT'])
@token_required(roles=['customer'])
def update_address(address_id):
    """Update an existing address completely"""
    current_user = request.current_user
    address = Address.query.filter_by(address_id=address_id, customer_id=current_user.customer_id).first()
    
    if not address:
        return jsonify({
            'success': False,
            'message': 'Address not found'
        }), 404
    
    data = request.json
    
    # Basic validation
    required_fields = ['name', 'mobile', 'pincode', 'locality', 'address_line', 'city', 'state_id', 'address_type']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({
                'success': False,
                'message': f'Missing required field: {field}'
            }), 400
    
    # Validate state_id exists
    state = State.query.get(data['state_id'])
    if not state:
        return jsonify({
            'success': False,
            'message': 'Invalid state selected'
        }), 400
    
    # Update all fields
    address.name = data['name']
    address.mobile = data['mobile']
    address.pincode = data['pincode']
    address.locality = data['locality']
    address.address_line = data['address_line']
    address.city = data['city']
    address.state_id = data['state_id']  # Changed from state to state_id
    address.landmark = data.get('landmark')
    address.alternate_phone = data.get('alternate_phone')
    address.address_type = data['address_type']
    
    # Update coordinates if provided
    if 'latitude' in data and 'longitude' in data:
        address.latitude = data['latitude']
        address.longitude = data['longitude']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Address updated successfully',
        'address': address.to_dict()
    })

@address_bp.route('/addresses/<int:address_id>', methods=['PATCH'])
@token_required(roles=['customer'])
def partial_update_address(address_id):
    """Partially update an existing address"""
    current_user = request.current_user
    address = Address.query.filter_by(address_id=address_id, customer_id=current_user.customer_id).first()
    
    if not address:
        return jsonify({
            'success': False,
            'message': 'Address not found'
        }), 404
    
    data = request.json
    
    # If state_id is being updated, validate it exists
    if 'state_id' in data:
        state = State.query.get(data['state_id'])
        if not state:
            return jsonify({
                'success': False,
                'message': 'Invalid state selected'
            }), 400
    
    # Update only provided fields
    for key, value in data.items():
        if hasattr(address, key):
            setattr(address, key, value)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Address updated successfully',
        'address': address.to_dict()
    })

@address_bp.route('/addresses/<int:address_id>', methods=['DELETE'])
@token_required(roles=['customer'])
def delete_address(address_id):
    """Delete an address"""
    current_user = request.current_user
    address = Address.query.filter_by(address_id=address_id, customer_id=current_user.customer_id).first()
    
    if not address:
        return jsonify({
            'success': False,
            'message': 'Address not found'
        }), 404
    
    db.session.delete(address)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Address deleted successfully'
    })

# Replace the Google Maps implementation with an alternative service
def reverse_geocode(latitude, longitude):
    """Convert coordinates to address details using a geocoding service"""
    try:
        # Example using Nominatim (OpenStreetMap)
        url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"
        headers = {'User-Agent': 'YourAppName/1.0'}  # Required by Nominatim
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'address' in data:
            address = data['address']
            
            # Extract address components
            address_details = {
                'address_line': data.get('display_name', ''),
                'city': address.get('city', address.get('town', '')),
                'state': address.get('state', ''),
                'state_id': None,
                'pincode': address.get('postcode', ''),
                'locality': address.get('suburb', address.get('neighbourhood', ''))
            }
            
            # Find state_id based on name
            if address_details['state']:
                state = State.query.filter_by(name=address_details['state']).first()
                if state:
                    address_details['state_id'] = state.state_id
            
            return address_details
        return None
    except Exception as e:
        print(f"Error in reverse geocoding: {str(e)}")
        return None

@address_bp.route('/addresses/location', methods=['POST'])
@token_required(roles=['customer'])
def save_current_location():
    """Save user's current location coordinates and reverse geocode to address"""
    data = request.json
    
    if 'latitude' not in data or 'longitude' not in data:
        return jsonify({
            'success': False,
            'message': 'Latitude and longitude are required'
        }), 400
    
    latitude = data['latitude']
    longitude = data['longitude']
    
   
    
    
    # Reverse geocode to get address details
    address_details = reverse_geocode(latitude, longitude)
    
    # Return location data with map URL and address details if available
    response = {
        'success': True,
        'location': {
            'latitude': latitude,
            'longitude': longitude,
            'map_url': f"https://maps.google.com/maps?q={latitude},{longitude}&z=15&output=embed"
        },
        'message': 'Location captured successfully'
    }
    
    if address_details:
        response['address_details'] = address_details
    
    return jsonify(response)

