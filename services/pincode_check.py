from dotenv import load_dotenv
import os

load_dotenv('/var/www/flask-backend/.env')

DELHIVERY_KEY = os.getenv("DELHIVERY_KEY")

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
                'Authorization': DELHIVERY_KEY,
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
