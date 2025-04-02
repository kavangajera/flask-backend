from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models.order import OrderHistory, OrderHistoryItem
from extensions import db

order_bp = Blueprint('order', __name__)

@order_bp.route('/orders', methods=['GET'])
@login_required
def list_orders():
    orders = OrderHistory.query.filter_by(customer_id=current_user.customer_id).all()
    orders_list = []
    for order in orders:
        order_dict = {
            'order_id': order.order_id,
            'customer_id': order.customer_id,
            'address': order.address,
            'date_time': order.date_time.isoformat() if order.date_time else None,
            'num_products': order.num_products,
            'total_price': float(order.total_price) if order.total_price else None,
            'delivery_charge': float(order.delivery_charge) if order.delivery_charge else None,
            'final_payment': float(order.final_payment) if order.final_payment else None,
            'items': []
        }
        for item in order.items:
            item_dict = {
                'item_id': item.item_id,
                'product_id': item.product_id,
                'quantity': item.quantity,
                'product_price': float(item.product_price) if item.product_price else None
            }
            order_dict['items'].append(item_dict)
        orders_list.append(order_dict)
    return jsonify(orders_list)

@order_bp.route('/order/create', methods=['POST'])
@login_required
def create_order():
    data = request.get_json()
    
    if not data or 'items' not in data:
        return jsonify({'error': 'No items provided'}), 400
    
    try:
        # Calculate order totals
        total_price = 0
        num_products = len(data['items'])
        
        # Create new order
        new_order = OrderHistory(
            customer_id=current_user.customer_id,
            address=data.get('address'),
            num_products=num_products,
            total_price=0,  # Will be updated after items
            delivery_charge=data.get('delivery_charge', 0),
            final_payment=0  # Will be updated after items
        )
        
        db.session.add(new_order)
        db.session.flush()  # Get the order_id
        
        # Add order items
        for item_data in data['items']:
            item = OrderHistoryItem(
                order_id=new_order.order_id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                product_price=item_data['product_price']
            )
            db.session.add(item)
            total_price += float(item_data['product_price']) * item_data['quantity']
        
        # Update order totals
        new_order.total_price = total_price
        new_order.final_payment = total_price + float(new_order.delivery_charge or 0)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order created successfully',
            'order_id': new_order.order_id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@order_bp.route('/order/<int:order_id>', methods=['GET'])
@login_required
def get_order(order_id):
    order = OrderHistory.query.filter_by(
        order_id=order_id,
        customer_id=current_user.customer_id
    ).first_or_404()
    
    order_dict = {
        'order_id': order.order_id,
        'customer_id': order.customer_id,
        'address': order.address,
        'date_time': order.date_time.isoformat() if order.date_time else None,
        'num_products': order.num_products,
        'total_price': float(order.total_price) if order.total_price else None,
        'delivery_charge': float(order.delivery_charge) if order.delivery_charge else None,
        'final_payment': float(order.final_payment) if order.final_payment else None,
        'items': []
    }
    
    for item in order.items:
        item_dict = {
            'item_id': item.item_id,
            'product_id': item.product_id,
            'quantity': item.quantity,
            'product_price': float(item.product_price) if item.product_price else None
        }
        order_dict['items'].append(item_dict)
    
    return jsonify(order_dict) 