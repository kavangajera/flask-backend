import requests
import json
from extensions import db
from models.order import Order,OrderDetail,OrderItem
from models.product import Product
from models.customer import Customer
from models.address import Address
from models.offline_customer import OfflineCustomer


def add_pickup_request(order_id):
    """Add a pickup request for an order to Delhivery API (normal function version)"""
    
    # Find order in database
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        raise ValueError('Order not found')
    
    # Get order address information
    address = Address.query.filter_by(address_id=order.address_id).first()
    if not address:
        raise ValueError('Order address not found')
    
    # Get customer information
    customer = None
    if order.customer_id:
        customer = Customer.query.filter_by(customer_id=order.customer_id).first()
    elif order.offline_customer_id:
        customer = OfflineCustomer.query.filter_by(customer_id=order.offline_customer_id).first()
    
    if not customer:
        raise ValueError('Customer not found')
    
    # Get state information
    state = address.state
    if not state:
        raise ValueError('State information not found')
    
    # Calculate total weight and build product description
    total_weight = 0.0
    products_desc = []
    
    for item in order.items:
        product_weight = getattr(item.product, 'weight', 0.5)  # Default weight
        total_weight += product_weight * item.quantity
        product_name = getattr(item.product, 'name', f"Product #{item.product_id}")
        products_desc.append(f"{product_name} x{item.quantity}")
    
    shipment_data = {
        "name": address.name,
        "add": f"{address.address_line}, {address.locality}",
        "city": address.city,
        "pin": address.pincode,
        "state": getattr(state, 'name', ""),
        "country": "India",
        "phone": address.mobile,
        "order": order_id,
        "payment_mode": "Prepaid" if order.payment_status == "paid" else "COD",
        "total_amount": float(order.total_amount),
        "cod_amount": 0 if order.payment_status == "paid" else float(order.total_amount),
        "weight": total_weight,
        "shipment_width": 10,
        "shipment_height": 10,
        "shipment_length": 10,
        "waybill": order.awb_number or "",
        "products_desc": ", ".join(products_desc)
    }

    payload = {
        "pickup_location": {
            "name": "mTm2",
            "add": "Address Line",
            "city": "City",
            "state": "State",
            "country": "India",
            "pin": "110001",
            "phone": "9999999999"
        },
        "shipments": [shipment_data]
    }

    url = "https://track.delhivery.com/api/cmu/create.json"
    headers = {
        "Authorization": "Token e3e340a4a9415a5282e8df1995fef1ceb82062cf"
    }

    response = requests.post(
        url,
        headers=headers,
        data={
            'data': json.dumps(payload),
            'format': 'json'
        }
    )

    if response.status_code != 200:
        raise Exception(f"Delhivery API error: {response.text}")

    response_data = response.json()

    try:
        if 'packages' in response_data and response_data['packages']:
            order.awb_number = response_data['packages'][0].get('waybill')

        if 'upload_wbn' in response_data:
            order.upload_wbn = response_data['upload_wbn']

        order.delivery_status = 'processing'
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Failed to update order with waybill: {str(e)}")

    return {
        'message': 'Pickup request created successfully',
        'order_id': order.order_id,
        'waybill': order.awb_number,
        'upload_wbn': order.upload_wbn,
        'response': response_data
    }