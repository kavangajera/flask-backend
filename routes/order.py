from flask import Blueprint, request, jsonify
from models.order import Order,OrderItem,OrderDetail, OrderStatusHistory, SerialNumber
from models.customer import Customer
from models.offline_customer import OfflineCustomer
from models.cart import Cart,CartItem
from models.product import Product,ProductColor,ProductModel,ModelSpecification,ProductSpecification
from models.address import Address
from models.device import DeviceTransaction
import decimal
from extensions import db
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import os
import requests
import json
from werkzeug.exceptions import BadRequest
import smtplib
from middlewares.Calculate_delivery_charge import calculateDelivery
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo
from decimal import Decimal


# Email configuration (replace with your SMTP details)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
# SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'sodagaramaan786@gmail.com')
# SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'gsin qzbq xuqw qihp')
SMTP_USERNAME = os.getenv('SMTP_USERNAME' , 'info@aesasolutions.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD' , 'xgha wzcd bxnw nfnm')


from middlewares.auth import token_required

order_bp = Blueprint('order', __name__)


@order_bp.route('/cart/updateitem', methods=['POST'])
@token_required(roles=['customer'])
def update_cart_item():
    data = request.get_json()
    
    # Validate request data
    required_fields = ['product_id', 'quantity']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    product_id = data['product_id']
    new_quantity = int(data['quantity'])
    model_id = data.get('model_id')
    color_id = data.get('color_id')
    
    # Get user's cart
    cart = Cart.query.filter_by(customer_id=request.current_user.customer_id).first()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404
    
    # Find the cart item
    query = CartItem.query.filter_by(
        cart_id=cart.cart_id,
        product_id=product_id
    )
    
    if model_id is not None:
        query = query.filter_by(model_id=model_id)
    if color_id is not None:
        query = query.filter_by(color_id=color_id)
    
    cart_item = query.first()
    
    if not cart_item:
        return jsonify({'error': 'Item not found in cart'}), 404
    
    # Check stock availability
    if color_id:
        color = ProductColor.query.get(color_id)
        if not color:
            return jsonify({'error': 'Color not found'}), 404
        if new_quantity > color.stock_quantity:
            return jsonify({
                'error': f'Only {color.stock_quantity} items available',
                'max_quantity': color.stock_quantity
            }), 400
    
    # Update quantity and price
    cart_item.quantity = new_quantity
    
    # Get current price (from color or model)
    if cart_item.color_id:
        color = ProductColor.query.get(cart_item.color_id)
        price = color.price
    else:
        product = Product.query.get(cart_item.product_id)
        price = product.base_price
    
    cart_item.total_item_price = decimal.Decimal(price) * decimal.Decimal(new_quantity)
    
    # Update cart total
    cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
    cart.total_cart_price = sum(decimal.Decimal(item.total_item_price) for item in cart_items)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Cart updated successfully',
        'cart_id': cart.cart_id,
        'total_cart_price': float(cart.total_cart_price)
    }), 200




@order_bp.route('/cart/additem', methods=['POST'])
@token_required(roles=['customer'])
def add_item_to_cart():
    data = request.get_json()
    
    # Validate request data
    required_fields = ['product_id']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    product_id = data.get('product_id')
    model_id = data.get('model_id')
    color_id = data.get('color_id')
    # spec_id = data.get('spec_id')
    quantity = data.get('quantity', 1)
    
    # Fetch the product
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    # Handle pricing based on product type
    price = None
    if product.product_type == 'variable':
        if not color_id and not model_id:
            return jsonify({'error': 'Color and Model selection required for variable products'}), 400
        # Get price from model/color combination
        model = ProductModel.query.get(model_id)
        if model:
            color = next((c for c in model.colors if c.color_id == color_id), None)
            if color:
                price = color.price
    elif product.product_type == 'single':
        if color_id:
            color = ProductColor.query.get(color_id)
            price = color.price
        
    
    if not price:
        return jsonify({'error': 'Could not determine product price'}), 400
    
    # Calculate the total price for this item
    total_item_price = decimal.Decimal(price) * decimal.Decimal(quantity)
    
    # Check if the user already has a cart, if not create one
    cart = Cart.query.filter_by(customer_id=request.current_user.customer_id).first()
    if not cart:
        cart = Cart(customer_id=request.current_user.customer_id)
        db.session.add(cart)
        db.session.flush()  # Flush to get the cart_id without committing
    
    # Check if the item already exists in the cart
    existing_item = CartItem.query.filter_by(
        cart_id=cart.cart_id,
        product_id=product_id,
        model_id=model_id,
        color_id=color_id,
        # spec_id=spec_id
    ).first()
    
    if existing_item:
        # Update existing item quantity and price
        existing_item.quantity += quantity
        existing_item.total_item_price = decimal.Decimal(existing_item.quantity) * decimal.Decimal(price)
    else:
        # Create new cart item
        cart_item = CartItem(
            cart_id=cart.cart_id,
            product_id=product_id,
            model_id=model_id,
            color_id=color_id,
            # spec_id=spec_id,
            quantity=quantity,
            total_item_price=total_item_price
        )
        db.session.add(cart_item)
    
    # Update the cart's total price
    cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
    cart.total_cart_price = sum(decimal.Decimal(item.total_item_price) for item in cart_items)
    
    # Commit all changes
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Item added to cart successfully',
        'cart_id': cart.cart_id,
        'total_cart_price': float(cart.total_cart_price)
    }), 200



# Delete Item:
@order_bp.route('/cart/deleteitem', methods=['POST'])
@token_required(roles=['customer'])
def delete_item_from_cart():
    data = request.get_json()
    
    # Validate request data
    required_fields = ['product_id']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    product_id = data.get('product_id')
    model_id = data.get('model_id')
    color_id = data.get('color_id')
    # spec_id = data.get('spec_id')
    quantity_to_remove = data.get('quantity', 1)
    
    # Check if the user has a cart
    cart = Cart.query.filter_by(customer_id=request.current_user.customer_id).first()
    if not cart:
        return jsonify({'error': 'No cart found for this user'}), 404
    
    # Find the cart item using product details
    query = CartItem.query.filter_by(
        cart_id=cart.cart_id,
        product_id=product_id
    )
    
    # Add optional filters if they were provided
    if model_id is not None:
        query = query.filter_by(model_id=model_id)
    if color_id is not None:
        query = query.filter_by(color_id=color_id)
    # if spec_id is not None:
    #     query = query.filter_by(spec_id=spec_id)
    
    cart_item = query.first()
    
    if not cart_item:
        return jsonify({'error': 'Item not found in cart'}), 404
    
    # If quantity to remove is less than current quantity, just reduce quantity
    if quantity_to_remove < cart_item.quantity:
        cart_item.quantity -= quantity_to_remove
        
        # Recalculate the item price
        # Get the price from the product color
        if cart_item.color_id:
            product_color = ProductColor.query.get(cart_item.color_id)
            if not product_color:
                return jsonify({'error': 'Product color not found'}), 500
            price = product_color.price
        else:
            # This should not happen based on your model, but just in case
            return jsonify({'error': 'Color ID is required'}), 500
        
        # Update item price
        cart_item.total_item_price = decimal.Decimal(cart_item.quantity) * decimal.Decimal(price)
    else:
        # Remove the entire cart item
        db.session.delete(cart_item)
    
    # Recalculate the cart's total price
    # Get all remaining items after the current session changes
    db.session.flush()
    remaining_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
    
    if remaining_items:
        cart.total_cart_price = sum(decimal.Decimal(item.total_item_price) for item in remaining_items)
    else:
        cart.total_cart_price = 0
    
    # Commit all changes
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Item removed from cart successfully',
        'cart_id': cart.cart_id,
        'total_cart_price': float(cart.total_cart_price)
    }), 200

@order_bp.route('/cart/getbycustid' , methods=['GET'])
@token_required(roles=['customer'])
def get_cart_by_customer_id():

    customer_id=request.current_user.customer_id
    cart = Cart.query.filter_by(customer_id=customer_id).first()
    
    if not cart:
        return jsonify({
            'success': True,
            'cart': {
                'cart_id': None,
                'customer_id': customer_id,
                'total_price': 0,
                'items': [],
                'item_count': 0
            }
        }), 200
    
    # Get all items in the cart with detailed information
    cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
    
    items_list = []
    for item in cart_items:
        # Get product details
        product = Product.query.get(item.product_id)
        
        # Get model details if applicable
        model = None
        if item.model_id:
            model = ProductModel.query.get(item.model_id)
        
        # Get color details if applicable
        color = None
        if item.color_id:
            color = ProductColor.query.get(item.color_id)
        
        # Get product specification details if applicable
        product_specifications = []
        if product:
            prod_specs = ProductSpecification.query.filter_by(product_id=product.product_id).all()
            for spec in prod_specs:
                product_specifications.append({
                    'spec_id': spec.spec_id,
                    'key': spec.key,
                    'value': spec.value
                })
        
        # Get model specification details if applicable
        model_specifications = []
        if model:
            mod_specs = ModelSpecification.query.filter_by(model_id=model.model_id).all()
            for spec in mod_specs:
                model_specifications.append({
                    'spec_id': spec.spec_id,
                    'key': spec.key,
                    'value': spec.value
                })
        
        # Get product image (first one if available)
        product_image = None
        if product and hasattr(product, 'images') and product.images:
            product_image = product.images[0].image_url if product.images else None
        
        # Get color-specific image if available
        color_image = None
        if color and hasattr(color, 'images') and color.images:
            color_image = color.images[0].image_url if color.images else None
        
        # Construct detailed item information
        item_details = {
            'item_id': item.item_id,
            'product': {
                'product_id': product.product_id if product else None,
                'name': product.name if product else 'Unknown',
                'description': product.description if product else None,
                'product_type': product.product_type if product else None,
                'rating': float(product.rating) if product and product.rating else 0,
                'image_url': color_image or product_image,
                'specifications': product_specifications
            },
            'model': {
                'model_id': model.model_id if model else None,
                'name': model.name if model else None,
                'description': model.description if model else None,
                'specifications': model_specifications
            } if model else None,
            'color': {
                'color_id': color.color_id if color else None,
                'name': color.name if color else None,
                'price': float(color.price) if color else None,
                'original_price': float(color.original_price) if color and color.original_price else None,
                'stock_quantity': color.stock_quantity if color else None
            } if color else None,
            'quantity': item.quantity,
            'unit_price': float(item.total_item_price / item.quantity) if item.quantity > 0 else 0,
            'total_item_price': float(item.total_item_price),
            'added_at': item.added_at.isoformat() if hasattr(item, 'added_at') and item.added_at else None
        }
        
        items_list.append(item_details)
    
    # Calculate any potential discounts
    # This is a placeholder - implement your discount logic here
    subtotal = float(cart.total_cart_price)
    discount = 0  # Calculate any applicable discounts
    tax = 0  # Calculate any applicable taxes
    shipping = 0  # Calculate shipping costs
    total = subtotal - discount + tax + shipping
    
    response = {
        'success': True,
        'cart': {
            'cart_id': cart.cart_id,
            'customer_id': customer_id,
            'created_at': cart.created_at.isoformat() if hasattr(cart, 'created_at') and cart.created_at else None,
            'updated_at': cart.updated_at.isoformat() if hasattr(cart, 'updated_at') and cart.updated_at else None,
            'item_count': len(items_list),
            'items': items_list,
            'pricing': {
                'subtotal': subtotal,
                'discount': discount,
                'tax': tax,
                'shipping': shipping,
                'total': total
            }
        }
    }
    
    return jsonify(response), 200
    


@order_bp.route('/cart/clear', methods=['DELETE'])
@token_required(roles=['customer'])
def clear_cart():
    # Get the customer's cart
    customer_id=request.current_user.customer_id
    cart = Cart.query.filter_by(customer_id=customer_id).first()
    
    if not cart:
        return jsonify({
            'success': True,
            'message': 'Cart is already empty'
        }), 200
    
    # Delete all items in the cart
    CartItem.query.filter_by(cart_id=cart.cart_id).delete()
    
    # Reset cart total
    cart.total_cart_price = 0
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Cart cleared successfully'
    }), 200



@order_bp.route('/orders', methods=['GET'])
def get_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()

    return jsonify([{
        'order_id': order.order_id,
        'customer_id': order.customer_id,
        'address': {
            'address_id': order.address.address_id,
            'name': order.address.name,
            'mobile': order.address.mobile,
            'pincode': order.address.pincode,
            'locality': order.address.locality,
            'address_line': order.address.address_line,
            'city': order.address.city,
            'state': {
                'state_id': order.address.state.state_id,
                'name': order.address.state.name,
                'abbreviation': order.address.state.abbreviation
            },
            'landmark': order.address.landmark,
            'alternate_phone': order.address.alternate_phone,
            'address_type': order.address.address_type,
            'latitude': order.address.latitude,
            'longitude': order.address.longitude,
            'is_available': order.address.is_available
        },
        'total_items': order.total_items,
        'subtotal': float(order.subtotal),
        'discount_percent': float(order.discount_percent),
        'delivery_charge': float(order.delivery_charge),
        'tax_percent': float(order.tax_percent),
        'total_amount': float(order.total_amount),
        'channel': order.channel,
        'payment_status': order.payment_status,
        'fulfillment_status': order.fulfillment_status,
        'delivery_status': order.delivery_status,
        'delivery_method': order.delivery_method,
        'awb_number': order.awb_number,
        'order_status': order.order_status,  #  Added this line
        'payment_type': order.payment_type,
        'created_at': order.created_at.isoformat(),
        'items': [{
            'product_id': item.product_id,
            'model_id': item.model_id,
            'color_id': item.color_id,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'total_price': float(item.total_price),
            'image_url': item.product.images[0].image_url if item.product and item.product.images else None,
        } for item in order.items]
    } for order in orders])




@order_bp.route('/orders/rejected', methods=['GET'])
def get_rejected_orders():

    orders = Order.query.filter(Order.order_status == "REJECTED").order_by(Order.created_at.desc()).all()

    return jsonify([{
        'order_id': order.order_id,
        'customer_id': order.customer_id,
        'address': {
            'address_id': order.address.address_id,
            'name': order.address.name,
            'mobile': order.address.mobile,
            'pincode': order.address.pincode,
            'locality': order.address.locality,
            'address_line': order.address.address_line,
            'city': order.address.city,
            'state': {
                'state_id': order.address.state.state_id,
                'name': order.address.state.name,
                'abbreviation': order.address.state.abbreviation
            },
            'landmark': order.address.landmark,
            'alternate_phone': order.address.alternate_phone,
            'address_type': order.address.address_type,
            'latitude': order.address.latitude,
            'longitude': order.address.longitude,
            'is_available': order.address.is_available  #  Added this line

        },
        'total_items': order.total_items,
        'subtotal': float(order.subtotal),
        'discount_percent': float(order.discount_percent),
        'delivery_charge': float(order.delivery_charge),
        'tax_percent': float(order.tax_percent),
        'total_amount': float(order.total_amount),
        'channel': order.channel,
        'payment_status': order.payment_status,
        'fulfillment_status': order.fulfillment_status,
        'delivery_status': order.delivery_status,
        'delivery_method': order.delivery_method,
        'awb_number': order.awb_number,
        'order_status': order.order_status,
        'payment_type': order.payment_type,
        'created_at': order.created_at.isoformat(),
        'items': [{
            'product_id': item.product_id,
            'model_id': item.model_id,
            'color_id': item.color_id,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'total_price': float(item.total_price),
            'image_url': item.product.images[0].image_url if item.product and item.product.images else None,
        } for item in order.items]
    } for order in orders])



@order_bp.route('/orders', methods=['POST'])
@token_required(roles=['admin'])
def create_order():
    data = request.get_json()

    # Validate customer
    customer = OfflineCustomer.query.get(data.get('customer_id'))
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404

    # Get customer's default address
    address = Address.query.filter_by(offline_customer_id=customer.customer_id).first()
    if not address:
        return jsonify({'error': 'No address found for customer'}), 404

    subtotal = 0
    total_discount_amount = 0
    order_items = []
    stock_updates = []

    # Prepare order items and check stock
    for item in data.get('items', []):
        product = Product.query.get(item['product_id'])
        if not product:
            return jsonify({'error': f"Product {item['product_id']} not found"}), 404

        color = ProductColor.query.get(item.get('color_id')) if item.get('color_id') else None
        model = ProductModel.query.get(item.get('model_id')) if item.get('model_id') else None

        if color and color.stock_quantity < item['quantity']:
            return jsonify({
                'error': f"Not enough stock for color '{color.name}'. Available: {color.stock_quantity}"
            }), 400

        # Use provided unit_price if available, otherwise use color price
        unit_price = item.get('unit_price') if 'unit_price' in item else (color.price if color else 0)
        
        # Calculate item subtotal (before discount)
        item_subtotal = unit_price * item['quantity']
        
        # Calculate item discount if provided
        item_discount_percent = item.get('extra_discount_percent', 0)
        item_discount_amount = (item_subtotal * item_discount_percent) / 100
        
        # Calculate total price after discount
        total_price = item_subtotal - item_discount_amount

        # Add to order totals
        subtotal += item_subtotal
        total_discount_amount += item_discount_amount

        order_items.append({
            'product_id': item['product_id'],
            'model_id': item.get('model_id'),
            'color_id': item.get('color_id'),
            'quantity': item['quantity'],
            'unit_price': unit_price,
            'discount_percent': item_discount_percent,
            'discount_amount': item_discount_amount,
            'total_price': total_price
        })

        # Keep track of stock updates
        if color:
            color.stock_quantity -= item['quantity']
            stock_updates.append(color)

    # Apply any order-level discount if needed (optional)
    order_discount_percent = data.get('discount_percent', 0)
    order_discount_amount = (subtotal * order_discount_percent) / 100
    
    # Total discount combines item-level and order-level discounts
    total_discount_amount += order_discount_amount

    # Calculate delivery charge
    delivery_charge = calculateDelivery(subtotal)
    
    # Calculate amount after discounts
    amount_after_discount = subtotal - total_discount_amount
    
    # Calculate GST (assumed 18% based on original code)
    gst = subtotal - (subtotal / Decimal('1.18'))
    
    # Subtotal without GST
    subtotal_without_gst = subtotal - gst
    
    # Calculate final total
    total_amount = amount_after_discount + delivery_charge

    try:
        # Get the next order_index value
        max_order = db.session.query(db.func.max(Order.order_index)).scalar() or 0
        next_order_index = max_order + 1
        
        # Current date for order_id generation
        current_date = datetime.now(tz=ZoneInfo('Asia/Kolkata'))
        current_year = current_date.year
        
        # Create and add order with explicit order_index
        order = Order(
            order_index=next_order_index,
            offline_customer_id=customer.customer_id,
            address_id=address.address_id,
            total_items=len(order_items),
            subtotal=subtotal_without_gst,  # Subtotal without GST
            discount_percent=order_discount_percent,  # Order-level discount percent
            discount_amount=total_discount_amount,  # Combined total discount amount
            delivery_charge=delivery_charge,
            tax_percent=data.get('tax_percent', 0),
            total_amount=total_amount,
            gst=gst,
            channel=data.get('channel', 'offline'),
            payment_status='pending',
            order_status='APPROVED',
            payment_type=data.get('payment_type', 'cod'),
            fulfillment_status=data.get('fulfillment_status', False),
            delivery_status=data.get('delivery_status', 'intransit'),
            delivery_method=data.get('delivery_method', 'shipping'),
            created_at=current_date
        )
        
        next_year = current_year + 1
        next_year = str(next_year)
        current_year = str(current_year)    
        order.order_id = f"{current_year}{next_year[2:]}#{next_order_index}"
        
        db.session.add(order)
        db.session.flush()  # Generate order_id

        # Add order items
        for item in order_items:
            order_item = OrderItem(
                order_id=order.order_id,
                product_id=item['product_id'],
                model_id=item.get('model_id'),
                color_id=item.get('color_id'),
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                discount_percent=item.get('discount_percent', 0),  # Store item discount percent
                discount_amount=item.get('discount_amount', 0),    # Store item discount amount
                total_price=item['total_price']
            )
            
            db.session.add(order_item)
            db.session.flush()  # Generate order_item.item_id

            for i in range(1, order_item.quantity + 1):
                order_detail = OrderDetail(
                    item_id=order_item.item_id,
                    order_id=order.order_id,
                    product_id=order_item.product_id
                )
                db.session.add(order_detail)
            
        # Apply stock updates
        for color in stock_updates:
            db.session.add(color)
            if color.stock_quantity <= color.threshold:
                print(f"Warning: Product color {color.name} stock is below threshold ({color.stock_quantity}/{color.threshold})")

        db.session.commit()

        return jsonify({
            'message': 'Order created successfully', 
            'order_id': order.order_id,
            'timestamp': current_date.isoformat()
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500




@order_bp.route('/order/place-order', methods=['POST'])
@token_required(roles=['customer'])
def place_order():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['address_id', 'payment_status', 'delivery_method']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Get customer's cart
    customer_id = request.current_user.customer_id
    cart = Cart.query.filter_by(customer_id=customer_id).first()
    
    if not cart or not cart.items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Verify address belongs to customer
    address = Address.query.get(data['address_id'])
    if not address or address.customer_id != customer_id:
        return jsonify({'error': 'Invalid address for this customer'}), 404
    
    # Get all items from cart
    cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
    if not cart_items:
        return jsonify({'error': 'No items in cart'}), 400
    
    # Verify stock availability for all items
    for item in cart_items:
        if item.color_id:
            color = ProductColor.query.get(item.color_id)
            if not color:
                return jsonify({'error': f'Product color not found for item {item.item_id}'}), 404
            if item.quantity > color.stock_quantity:
                return jsonify({
                    'error': f'Not enough stock for product. Only {color.stock_quantity} available.',
                    'product_id': item.product_id,
                    'color_id': item.color_id
                }), 400
    
    # Calculate order totals
    # subtotal=cart.get('total_cart_price')
    subtotal=cart.total_cart_price
    discount_amount = (subtotal * data.get('discount_percent', 0)) / 100

    delivery_charge=calculateDelivery(subtotal)
    total_amount = subtotal - discount_amount  + delivery_charge

    gst = subtotal - (subtotal / Decimal('1.18'))    
    subtotal-=gst
    
    
    try:
        # Get the next order_index value
        # Method 1: Get the max order_index and increment it
        max_order = db.session.query(db.func.max(Order.order_index)).scalar() or 0
        next_order_index = max_order + 1
        
        # Current date for order_id generation
        current_date = datetime.now(tz=ZoneInfo('Asia/Kolkata'))
        current_year = current_date.year
        
        # Create new order with explicit order_index
        order = Order(
            order_index=next_order_index,  # Set the order_index explicitly
            customer_id=customer_id,
            address_id=data['address_id'],
            total_items=len(cart_items),
            subtotal=subtotal,
            discount_percent=data.get('discount_percent' , 0),
            delivery_charge=delivery_charge,
            tax_percent=data.get('tax_percent', 0),
            total_amount=total_amount,
            gst=gst,
            channel='online',  # Hardcoded for this endpoint
            payment_status=data['payment_status'],
            payment_type=data.get('payment_type', 'cod'),
            fulfillment_status=False,
            delivery_status='pending',
            delivery_method=data['delivery_method'],
            awb_number=data.get('awb_number'),
            created_at=current_date
        )
        
        # Manually set the order_id with the expected format (do not rely on __init__)
        next_year = current_year + 1
        next_year = str(next_year)
        current_year = str(current_year)    
        order.order_id = f"{current_year}{next_year[2:]}#{next_order_index}"
        
        db.session.add(order)
        db.session.flush()
        
        # Create order items from cart items and order details
        order_items = []
        for cart_item in cart_items:
            # Get product and price information
            product = Product.query.get(cart_item.product_id)
            if not product:
                db.session.rollback()
                return jsonify({'error': f'Product not found: {cart_item.product_id}'}), 404
            
            # Determine unit price
            unit_price = 0
            if cart_item.color_id:
                color = ProductColor.query.get(cart_item.color_id)
                if color:
                    unit_price = color.price
                    
                    # Update stock quantity
                    color.stock_quantity -= cart_item.quantity
                    if color.stock_quantity < 0:
                        db.session.rollback()
                        return jsonify({'error': f'Not enough stock for product {product.name}'}), 400
            else:
                unit_price = product.base_price
            
            # Create order item
            order_item = OrderItem(
                order_id=order.order_id,
                product_id=cart_item.product_id,
                model_id=cart_item.model_id,
                color_id=cart_item.color_id,
                quantity=cart_item.quantity,
                unit_price=unit_price,
                total_price=cart_item.total_item_price
            )
            
            db.session.add(order_item)
            db.session.flush()  # Get item_id
            
            # Create order details for each quantity
            for i in range(1, cart_item.quantity + 1):
                order_detail = OrderDetail(
                    item_id=order_item.item_id,
                    order_id=order.order_id,
                    product_id=cart_item.product_id
                )
                db.session.add(order_detail)
            
            order_items.append(order_item)
        
        # Clear cart items
        for item in cart_items:
            db.session.delete(item)
        
        # Reset cart total
        cart.total_cart_price = 0
        
        db.session.commit()


        try:
            subject = f"New Order Placed: {order.order_id}"
            body = f"""
            A new order has been placed with the following details:
            
            Order ID: {order.order_id}
            Customer ID: {customer_id}
            Total Items: {order.total_items}
            Subtotal: {order.subtotal}
            Total Amount: {order.total_amount}
            Payment Status: {order.payment_status}
            Delivery Method: {order.delivery_method}
            
            Please review the order in the admin panel.
            """
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = SMTP_USERNAME
            msg['To'] = 'sodagaramaan78692@gmail.com'
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        except Exception as email_error:
            print(f"Failed to send admin notification email: {email_error}")
            # Don't fail the order if email fails
        
        
        return jsonify({
            'success': True,
            'message': 'Order placed successfully',
            'order': {
                'order_id': order.order_id,
                'customer_id': customer_id,
                'total_items': order.total_items,
                'subtotal': float(order.subtotal),
                'discount_percent': float(order.discount_percent),
                'delivery_charge': float(order.delivery_charge),
                'tax_percent': float(order.tax_percent),
                'total_amount': float(order.total_amount),
                'payment_status': order.payment_status,
                'fulfillment_status': order.fulfillment_status,
                'payment_type': order.payment_type,
                'delivery_method': order.delivery_method,
                'created_at': order.created_at.isoformat(),
                'items': [{
                    'product_id': item.product_id,
                    'model_id': item.model_id,
                    'color_id': item.color_id,
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                    'total_price': float(item.total_price)
                } for item in order_items]
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error creating order: {str(e)}'}), 500



@order_bp.route('/orders/<string:order_id>/items-expanded', methods=['GET'])
def get_order_items_expanded(order_id):
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        expanded_items = []
        for item in order.items:
            # Get the product and check its type
            product = Product.query.get(item.product_id) if item.product_id else None
            
            # Initialize variables
            product_name = None
            model_name = None
            color_name = None
            
            if product:
                product_name = product.name
                
                # Handle differently based on product type
                if product.product_type == 'variable':
                    # For variable products, get model and color information
                    if hasattr(item, 'model_id') and item.model_id:
                        model = ProductModel.query.get(item.model_id)
                        model_name = model.name if model else None
                    
                    if hasattr(item, 'color_id') and item.color_id:
                        color = ProductColor.query.get(item.color_id)
                        color_name = color.name if color else None
                
                elif product.product_type == 'single':
                    # For single products, only color information might be relevant
                    if hasattr(item, 'color_id') and item.color_id:
                        color = ProductColor.query.get(item.color_id)
                        color_name = color.name if color else None
            
            # Create expanded items for each quantity
            for _ in range(item.quantity):
                expanded_items.append({
                    'item_id': item.item_id,
                    'product_id': item.product_id,
                    'product_type': product.product_type if product else None,
                    'model_id': item.model_id if hasattr(item, 'model_id') else None,
                    'color_id': item.color_id if hasattr(item, 'color_id') else None,
                    'unit_price': float(item.unit_price),
                    'total_price': float(item.unit_price),
                    'product_name': product_name,
                    'model_name': model_name if model_name else product_name,
                    'color_name': color_name,
                    'status': getattr(item, 'status', None)  # Safely get status if it exists
                })
        
        return jsonify({
            'order_id': order.order_id,
            'customer_id': order.customer_id,
            'total_items': len(expanded_items),
            'subtotal': float(order.subtotal),
            'total_amount': float(order.total_amount),
            'payment_status': order.payment_status,
            'fulfillment_status': order.fulfillment_status,
            'payment_type': order.payment_type,
            'delivery_status': order.delivery_status,
            'created_at': order.created_at.isoformat(),
            'items': expanded_items
        })
    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_order_items_expanded: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

# @order_bp.route('/orders/<string:order_id>/details-expanded', methods=['GET'])
# def get_order_details_expanded(order_id):
#     try:
#         # Get the order and verify it exists
#         order = Order.query.get(order_id)
#         if not order:
#             return jsonify({'error': 'Order not found'}), 404
        
#         # Get all order details for this order
#         order_details = OrderDetail.query.filter_by(order_id=order_id).all()
        
#         expanded_details = []
#         for detail in order_details:
#             # Get related order item
#             order_item = detail.item
            
#             # Safely access related objects
#             product_name = order_item.product.name if order_item.product and hasattr(order_item, 'product') else None
#             model_name = order_item.model.name if order_item.model and hasattr(order_item, 'model') else None
#             color_name = order_item.color.name if order_item.color and hasattr(order_item, 'color') else None
            
#             expanded_details.append({
#                 'detail_id': detail.id,
#                 'item_id': detail.item_id,
#                 'order_id': detail.order_id,
#                 'product_id': detail.product_id,
#                 'sr_no': detail.sr_no,
#                 'product_name': product_name,
#                 'model_name': model_name if model_name else product_name,
#                 'color_name': color_name,
#                 'unit_price': float(order_item.unit_price) if order_item else 0,
#                 'status': getattr(detail, 'status', None),
#                 'created_at': detail.created_at.isoformat() if hasattr(detail, 'created_at') and detail.created_at else None
#             })
        
#         # Include address information like in the /orders endpoint
#         address_data = None
#         if order.address:
#             address_data = {
#                 'address_id': order.address.address_id,
#                 'name': order.address.name,
#                 'mobile': order.address.mobile,
#                 'pincode': order.address.pincode,
#                 'locality': order.address.locality,
#                 'address_line': order.address.address_line,
#                 'city': order.address.city,
#                 'state': {
#                     'state_id': order.address.state.state_id,
#                     'name': order.address.state.name,
#                     'abbreviation': order.address.state.abbreviation
#                 },
#                 'landmark': order.address.landmark,
#                 'alternate_phone': order.address.alternate_phone,
#                 'address_type': order.address.address_type,
#                 'latitude': order.address.latitude,
#                 'longitude': order.address.longitude,
#                 'is_available': order.address.is_available  #  Make sure this is included
#             }
        
#         return jsonify({
#             'order_id': order.order_id,
#             'customer_id': order.customer_id,
#             'offline_customer_id': order.offline_customer_id,
#             'customer_type': 'offline' if order.offline_customer_id else 'online',
#             'total_details': len(expanded_details),
#             'subtotal': float(order.subtotal),
#             'total_amount': float(order.total_amount),
#             'payment_status': order.payment_status,
#             'fulfillment_status': order.fulfillment_status,
#             'delivery_status': order.delivery_status,
#             'created_at': order.created_at.isoformat(),
#             'awb_number': order.awb_number,
#             'payment_type': order.payment_type,
#             'upload_wbn': order.upload_wbn,
#             'address': address_data,
#             'details': expanded_details
#         })

#     except Exception as e:
#         print(f"Error in get_order_details_expanded: {str(e)}")
#         return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@order_bp.route('/orders/<string:order_id>/details-expanded', methods=['GET'])
def get_order_details_expanded(order_id):
    try:
        # Get the order and verify it exists
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Get all order details for this order
        order_details = OrderDetail.query.filter_by(order_id=order_id).all()
        
        expanded_details = []
        for detail in order_details:
            # Get related order item
            order_item = detail.item
            
            # Safely access related objects
            product_name = order_item.product.name if order_item.product and hasattr(order_item, 'product') else None
            
            # Try to get model name through proper relationships
            model_name = None
            if order_item.model and hasattr(order_item, 'model'):
                model_name = order_item.model.name
            # If model is not available but we have product_id, try to find the default model
            elif order_item.product_id:
                # For single products, there should be one model - get it directly
                default_model = ProductModel.query.filter_by(product_id=order_item.product_id).first()
                if default_model:
                    model_name = default_model.name
            
            color_name = order_item.color.name if order_item.color and hasattr(order_item, 'color') else None
            
            # Use model name from database but fall back to product name if model_name is None
            # This handles products created before the model_name field was implemented
            expanded_details.append({
                'detail_id': detail.id,
                'item_id': detail.item_id,
                'order_id': detail.order_id,
                'product_id': detail.product_id,
                'sr_no': detail.sr_no,
                'product_name': product_name,
                'model_name': model_name,  # Fallback to product_name if model_name is None
                'color_name': color_name,
                'unit_price': float(order_item.unit_price) if order_item else 0,
                'status': getattr(detail, 'status', None),
                'created_at': detail.created_at.isoformat() if hasattr(detail, 'created_at') and detail.created_at else None
            })
        
        # Include address information like in the /orders endpoint
        address_data = None
        if order.address:
            address_data = {
                'address_id': order.address.address_id,
                'name': order.address.name,
                'mobile': order.address.mobile,
                'pincode': order.address.pincode,
                'locality': order.address.locality,
                'address_line': order.address.address_line,
                'city': order.address.city,
                'state': {
                    'state_id': order.address.state.state_id,
                    'name': order.address.state.name,
                    'abbreviation': order.address.state.abbreviation
                },
                'landmark': order.address.landmark,
                'alternate_phone': order.address.alternate_phone,
                'address_type': order.address.address_type,
                'latitude': order.address.latitude,
                'longitude': order.address.longitude,
                'is_available': order.address.is_available  #  Make sure this is included
            }
        
        return jsonify({
            'order_id': order.order_id,
            'customer_id': order.customer_id,
            'offline_customer_id': order.offline_customer_id,
            'customer_type': 'offline' if order.offline_customer_id else 'online',
            'total_details': len(expanded_details),
            'subtotal': float(order.subtotal),
            'total_amount': float(order.total_amount),
            'payment_status': order.payment_status,
            'fulfillment_status': order.fulfillment_status,
            'delivery_status': order.delivery_status,
            'created_at': order.created_at.isoformat(),
            'awb_number': order.awb_number,
            'payment_type': order.payment_type,
            'upload_wbn': order.upload_wbn,
            'address': address_data,
            'details': expanded_details
        })

    except Exception as e:
        print(f"Error in get_order_details_expanded: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500





# @order_bp.route('/orders/save-sr-numbers', methods=['POST'])
# def save_serial_numbers():
#     try:
#         data = request.get_json()
        
#         # Validate request data
#         if not data or not isinstance(data, list):
#             return jsonify({'error': 'Invalid request data format'}), 400
        
#         # Get order details first to get order information
#         order_details = []
#         for sr_data in data:
#             detail = OrderDetail.query.get(sr_data['detail_id'])
#             if not detail:
#                 continue
#             order_details.append(detail)
        
#         if not order_details:
#             return jsonify({'error': 'No valid order details found'}), 400
        
#         # Get the order from the first detail (all details should belong to the same order)
#         order = order_details[0].order

#         # Fallback SKU settings
#         sku_prefix = 'sku'
#         fallback_sku_counter = 123  # Starting point for fallback SKUs

#         # Process each serial number
#         for index, (sr_data, detail) in enumerate(zip(data, order_details)):
#             sr_no = sr_data.get('sr_no')
#             if not sr_no:
#                 continue  # Skip if no SR number provided
                
#             # Update the SR number in OrderDetail
#             detail.sr_no = sr_no
#             db.session.add(detail)

#             # Determine the SKU (with fallback)
#             if detail.item and hasattr(detail.item, 'sku') and detail.item.sku:
#                 sku_id = detail.item.sku
#             else:
#                 sku_id = f"{sku_prefix}{fallback_sku_counter + index}"

#             # Create OUT transaction for this device
            # transaction = DeviceTransaction(
            #     device_srno=sr_no,
            #     device_name=detail.item.product.name if detail.item and detail.item.product else 'Unknown Device',
            #     sku_id=sku_id,
            #     order_id=order.order_id,
            #     in_out=2,  # OUT transaction
            #     create_date=datetime.now(tz=ZoneInfo('Asia/Kolkata')),
            #     price=float(detail.item.unit_price) if detail.item and hasattr(detail.item, 'unit_price') else None,
            #     remarks=f"Device sold in order {order.order_id}"
            # )
            # db.session.add(transaction)
        
#         db.session.commit()
        
#         return jsonify({
#             'success': True,
#             'message': 'Serial numbers saved successfully and OUT transactions created'
#         })
        
#     except Exception as e:
#         db.session.rollback()
#         print(f"Error saving serial numbers: {str(e)}")
#         return jsonify({
#             'error': 'Failed to save serial numbers',
#             'details': str(e)
#         }), 500

@order_bp.route('/save-sr-number', methods=['POST'])
@token_required(roles=['admin'])
def save_sr_number():
    try:
        data = request.get_json()

        if not isinstance(data, list):
            raise BadRequest('Invalid input: Expected an array.')

        detail_id = data[0].get('detail_id')
        if not detail_id:
            return jsonify({'error': 'Missing detail_id'}), 400

        # Step 1: Find Detail
        detail = OrderDetail.query.get(detail_id)
        if not detail:
            return jsonify({'error': 'Detail not found'}), 404

        # Step 2: Get Order using order_id
        order = Order.query.get(detail.order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Step 3: Get Customer using cust_id
        customer = Customer.query.get(order.customer_id)
        if not customer:
            customer=OfflineCustomer.query.get(order.offline_customer_id)
            if not customer:
                return jsonify({'error': 'Customer not found'}), 404

        # Process each detail in the input array
        for item in data:
            detail = OrderDetail.query.get(item.get('detail_id'))
            if not detail:
                continue  # Skip if not found

            sr_no = item.get('sr_no')
            if not sr_no:
                continue  # Skip if SR number is missing

            detail.sr_no = sr_no
            db.session.add(detail)

            # Construct a simple SKU ID format
            sku_id = f"{detail.id}-{sr_no}-{order.order_id}"

            transaction = DeviceTransaction(
                device_srno=sr_no,
                device_name=detail.item.product.name if detail.item and detail.item.product else 'Unknown Device',
                sku_id=sku_id,
                order_id=order.order_id,
                in_out=2,  # OUT transaction
                create_date=datetime.now(tz=ZoneInfo('Asia/Kolkata')),
                price=float(detail.item.unit_price) if detail.item and hasattr(detail.item, 'unit_price') else None,
                remarks=f"Device sold to {customer.name}"
            )
            db.session.add(transaction)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Serial numbers saved successfully and OUT transactions created'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return jsonify({
            'error': 'Failed to save serial numbers',
            'details': str(e)
        }), 500



@order_bp.route('/order/add-to-order', methods=['POST'])
@token_required(roles=['customer'])
def add_to_order():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['product_id', 'address_id', 'payment_status', 'delivery_method', 'quantity']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Validate quantity is a positive integer
    try:
        quantity = int(data['quantity'])
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be a positive integer'}), 400
        data['quantity'] = quantity
    except (ValueError, TypeError):
        return jsonify({'error': 'Quantity must be a valid number'}), 400
    
    # Optional fields with defaults
    model_id = data.get('model_id')
    color_id = data.get('color_id')
    from decimal import Decimal

    discount_percent = Decimal(str(data.get('discount_percent', 0)))
    tax_percent = Decimal(str(data.get('tax_percent', 0)))
   
    
    # Get customer ID from token
    customer_id = request.current_user.customer_id
    
    # Verify address belongs to customer
    address = Address.query.get(data['address_id'])
    if not address or address.customer_id != customer_id:
        return jsonify({'error': 'Invalid address for this customer'}), 404
    
    # Get product information
    product = Product.query.get(data['product_id'])
    if not product:
        return jsonify({'error': f'Product not found: {data["product_id"]}'}), 404
    
    # Determine unit price and verify stock
    if color_id:
        color = ProductColor.query.get(color_id)
        if not color:
            return jsonify({'error': f'Product color not found: {color_id}'}), 404
        
        # Check if color belongs to this product
        if color.product_id != data['product_id']:
            return jsonify({'error': 'Color does not belong to this product'}), 400
        
        # Verify stock availability
        if data['quantity'] > color.stock_quantity:
            return jsonify({
                'error': f'Not enough stock for product. Only {color.stock_quantity} available.',
                'product_id': data['product_id'],
                'color_id': color_id
            }), 400
        
        unit_price = color.price
    
    # Calculate order totals
    subtotal = unit_price * data['quantity']
    total_item_price = subtotal
    
    # Calculate final amount
    discount_amount = (subtotal * discount_percent) / 100

    delivery_charge=calculateDelivery(subtotal)

    total_amount = subtotal - discount_amount  + delivery_charge

    from decimal import Decimal

    gst = subtotal - (subtotal / Decimal('1.18'))
    subtotal-=gst
    
    try:
        # Get the next order_index value
        max_order = db.session.query(db.func.max(Order.order_index)).scalar() or 0
        next_order_index = max_order + 1
        
        # Current date for order_id generation
        current_date = datetime.now(tz=ZoneInfo('Asia/Kolkata'))
        current_year = current_date.year
        # Create new order with explicit order_index
        order = Order(
            order_index=next_order_index,
            customer_id=customer_id,
            address_id=data['address_id'],
            total_items=data['quantity'],
            subtotal=subtotal,
            discount_percent=discount_percent,
            delivery_charge=delivery_charge,
            tax_percent=tax_percent,
            total_amount=total_amount,
            channel='online',
            gst=gst,
            payment_status=data['payment_status'],
            payment_type=data.get('payment_type', 'cod'),
            fulfillment_status=False,
            delivery_status='pending',
            delivery_method=data['delivery_method'],
            awb_number=data.get('awb_number'),
            created_at=current_date
        )
        
        # Manually set the order_id with the expected format (do not rely on __init__)
        next_year = current_year + 1
        next_year = str(next_year)
        current_year = str(current_year)    
        order.order_id = f"{current_year}{next_year[2:]}#{next_order_index}"
        
        db.session.add(order)
        db.session.flush()
        
        # Create order item
        order_item = OrderItem(
            order_id=order.order_id,
            product_id=data['product_id'],
            model_id=model_id,
            color_id=color_id,
            quantity=data['quantity'],
            unit_price=unit_price,
            total_price=total_item_price
        )
        
        db.session.add(order_item)
        db.session.flush()  # Get item_id
        
        # Create order details for each quantity
        for i in range(1, data['quantity'] + 1):
            order_detail = OrderDetail(
                item_id=order_item.item_id,
                order_id=order.order_id,
                product_id=data['product_id']
            )
            db.session.add(order_detail)
        
        # Update stock quantity if color is specified
        if color_id:
            color = ProductColor.query.get(color_id)
            color.stock_quantity -= data['quantity']
            if color.stock_quantity < 0:
                db.session.rollback()
                return jsonify({'error': f'Not enough stock for product {product.name}'}), 400
        else:
            # If we're tracking stock at the product level instead of color level
            if hasattr(product, 'stock_quantity'):
                product.stock_quantity -= data['quantity']
                if product.stock_quantity < 0:
                    db.session.rollback()
                    return jsonify({'error': f'Not enough stock for product {product.name}'}), 400
        
        db.session.commit()


        # Send email notification to admin after successful order placement
        try:
            subject = f"New Direct Order Placed: {order.order_id}"
            body = f"""
            A new direct order has been placed with the following details:
            
            Order ID: {order.order_id}
            Customer ID: {customer_id}
            Product ID: {data['product_id']}
            Quantity: {data['quantity']}
            Total Amount: {order.total_amount}
            Payment Status: {order.payment_status}
            Delivery Method: {order.delivery_method}
            
            Please review the order in the admin panel.
            """
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = SMTP_USERNAME
            msg['To'] = 'meetkoladiya6753@gmail.com'
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        except Exception as email_error:
            print(f"Failed to send admin notification email: {email_error}")
        
        return jsonify({
            'success': True,
            'message': 'Order placed successfully',
            'order': {
                'order_id': order.order_id,
                'customer_id': customer_id,
                'total_items': order.total_items,
                'subtotal': float(order.subtotal),
                'discount_percent': float(order.discount_percent),
                'delivery_charge': float(order.delivery_charge),
                'tax_percent': float(order.tax_percent),
                'total_amount': float(order.total_amount),
                'payment_status': order.payment_status,
                'delivery_method': order.delivery_method,
                'created_at': order.created_at.isoformat(),
                'items': [{
                    'product_id': order_item.product_id,
                    'model_id': order_item.model_id,
                    'color_id': order_item.color_id,
                    'quantity': order_item.quantity,
                    'unit_price': float(order_item.unit_price),
                    'total_price': float(order_item.total_price)
                }]
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error creating order: {str(e)}'}), 500
    


@order_bp.route('/customer/<int:customer_id>/orders', methods=['GET'])
def get_customer_orders(customer_id):
    """Get all orders for a specific customer"""
    try:
        # Get both online and offline orders for this customer
        orders = Order.query.filter(
            (Order.customer_id == customer_id) | 
            (Order.offline_customer_id == customer_id)
        ).order_by(Order.created_at.desc()).all()

        if not orders:
            return jsonify({'message': 'No orders found for this customer'}), 404

        return jsonify([{
            'order_id': order.order_id,
            'total_amount': float(order.total_amount),
            'payment_status': order.payment_status,
            'delivery_status': order.delivery_status,
            'order_status': order.order_status,
            'created_at': order.created_at.isoformat(),
            'item_count': order.total_items
        } for order in orders])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@order_bp.route('/order/<path:order_id>/items', methods=['GET'])
def get_order_items(order_id):
    """Get all items for a specific order with complete details"""
    try:
        # No need to unquote since Flask handles path conversion
        print(f"Looking for order: {order_id}")  # Debug log
        
        # Find exact match (including special characters)
        order = Order.query.filter_by(order_id=order_id).first()
        
        if not order:
            print(f"Order not found. Existing orders: {[o.order_id for o in Order.query.limit(10).all()]}")
            return jsonify({'message': 'Order not found'}), 404

        items = []
        for item in order.items:
            product = Product.query.get(item.product_id)
            product_image = product.images[0].image_url if product and product.images else None
            
            items.append({
                'product_id': item.product_id,
                'product_name': product.name if product else f"Product {item.product_id}",
                'product_image': product_image,
                'model': item.model.name if item.model else None,
                'color': item.color.name if item.color else None,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price),
                'serial_numbers': [sn.sr_number for sn in item.serial_numbers]
            })

        return jsonify({
            'order_id': order.order_id,
            'customer_id': order.customer_id or order.offline_customer_id,
            'created_at': order.created_at.isoformat(),
            'items': items,
            'delivery_status': order.delivery_status,
            'payment_status': order.payment_status,
            'order_status': order.order_status,  
            'total_amount': float(order.total_amount),
            'total_items': order.total_items
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@order_bp.route('/order/<string:order_id>/add-pickup-req', methods=['PUT'])
@token_required(roles=['admin'])      
def add_pickup_request(order_id):
    """Add a pickup request for an order to Delhivery API
    
    Takes an order ID and creates a pickup request with the Delhivery API
    """
    try:
        print(order_id)
        order = Order.query.filter_by(order_id=order_id).first()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Get order address information
        address = Address.query.filter_by(address_id=order.address_id).first()
        if not address:
            return jsonify({'error': 'Order address not found'}), 404
            
        # Get customer information
        customer = None
        if order.customer_id:
            customer = Customer.query.filter_by(customer_id=order.customer_id).first()
        elif order.offline_customer_id:
            customer = OfflineCustomer.query.filter_by(customer_id=order.offline_customer_id).first()
            
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
            
        # Get state information
        state = address.state
        if not state:
            return jsonify({'error': 'State information not found'}), 404
            
        # Calculate total weight and build product description
        total_weight = 0.0
        products_desc = []
        
        for item in order.items:
            # Assuming each product might have a weight attribute, if not you'll need to modify this
            product_weight = getattr(item.product, 'weight', 0.5)  # Default to 0.5 kg if not specified
            total_weight += product_weight * item.quantity
            
            # Build product description
            product_name = item.product.name if hasattr(item.product, 'name') else f"Product #{item.product_id}"
            products_desc.append(f"{product_name} x{item.quantity}")
        
        # Format the shipment data for Delhivery API
        shipment_data = {
            "name": address.name,
            "add": f"{address.address_line}, {address.locality}",
            "city": address.city,
            "pin": address.pincode,
            "state": state.name if hasattr(state, 'name') else "",
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
        
        # Prepare the full request payload for Delhivery API
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
        
        # Send request to Delhivery API
        DELHIVERY_KEY = os.getenv("DELHIVERY_KEY")
        url = "https://track.delhivery.com/api/cmu/create.json"
        headers = {
            "Authorization": "Token "+DELHIVERY_KEY
        }

        response = requests.post(
            url,
            headers=headers,
            data={
                'data': json.dumps(payload),
                'format': 'json'  #  Important to add this
            }
        )

        if response.status_code != 200:
            return jsonify({'error': 'Failed to create pickup request', 'details': response.text}), response.status_code

        response_data = response.json()
        
        # Update the order with waybill, upload_wbn and fulfillment_status
        try:
            if 'waybill' in response_data['packages'][0]:
                order.awb_number = response_data['packages'][0].get('waybill')
            
            if 'upload_wbn' in response_data:
                order.upload_wbn = response_data['upload_wbn']
                
            # Set delivery status to processing and fulfillment status to True
            order.delivery_status = 'processing'
            order.fulfillment_status = True  # This is the key change you wanted
            
            # Save changes to database
            db.session.commit()
            
            return jsonify({
                'message': 'Pickup request created successfully',
                'order_id': order.order_id,
                'waybill': order.awb_number,
                'upload_wbn': order.upload_wbn,
                'fulfillment_status': True,  # Added to response
                'delhivery_payload_sent': payload,   #  Add this line
                'response': response_data
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to update order: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# @order_bp.route('/order/<string:order_id>/track',methods=['GET'])
# @token_required(roles=['customer'])
# def track_order(order_id):

#        try:
#            order = Order.query.filter_by(order_id=order_id).first()
#            if not order:
#                return jsonify({'error': 'Order not found'}), 404
#            waybill=order.awb_number
#            if not waybill:
#                return jsonify({'error': 'Waybill not found'}), 404
#            # Call the API to track the order
           
#            DELHIVERY_KEY = os.getenv("DELHIVERY_KEY")
#            url = f"https://track.delhivery.com/api/v1/packages/json/?waybill={waybill}&token={DELHIVERY_KEY}"

#            response = requests.get(url)
#            response.raise_for_status()  # Raises HTTPError for bad responses (4xx/5xx)
#            return response.json()
#        except requests.exceptions.RequestException as e:
#         return {'error': str(e)}
       

@order_bp.route('/change-order-status/<string:order_id>' , methods=['POST'])
@token_required(roles=['admin'])
def change_order_status(order_id):
    try:

        data = request.get_json()

        order = Order.query.filter_by(order_id=order_id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Get customer email
        customer = None
        if order.customer_id:
            customer = Customer.query.get(order.customer_id)
        elif order.offline_customer_id:
            # Handle offline customer if needed
            pass
            
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        order.order_status = data.get('status')
        db.session.commit()
        
        # Send approval email to customer
        try:
            subject = f"Your Order #{order_id} Has Been {data.get('status')}"
            body = f"""
            Dear {customer.name},
            
            We're pleased to inform you that your order #{order_id} has been approved and is being processed.
            
            Order Details:
            - Order ID: {order_id}
            - Total Amount: {order.total_amount}
            - Status: Approved
            
            Thank you for shopping with us!
            
            Best regards,
            Your Store Team
            """
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = SMTP_USERNAME
            msg['To'] = customer.email
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        except Exception as email_error:
            print(f"Failed to send approval email: {email_error}")
            # Continue even if email fails
        
        return jsonify({'message': 'Order approved successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500




@order_bp.route('/approve-order/<string:order_id>', methods=['GET'])
@token_required(roles=['admin'])
def approve_order(order_id):
    try:
        order = Order.query.filter_by(order_id=order_id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Get customer email
        customer = None
        if order.customer_id:
            customer = Customer.query.get(order.customer_id)
        elif order.offline_customer_id:
            # Handle offline customer if needed
            pass
            
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        order.order_status = "APPROVED"
        db.session.commit()
        
        # Send approval email to customer
        try:
            subject = f"Your Order #{order_id} Has Been Approved"
            body = f"""
            Dear {customer.name},
            
            We're pleased to inform you that your order #{order_id} has been approved and is being processed.
            
            Order Details:
            - Order ID: {order_id}
            - Total Amount: {order.total_amount}
            - Status: Approved
            
            Thank you for shopping with us!
            
            Best regards,
            Your Store Team
            """
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = SMTP_USERNAME
            msg['To'] = customer.email
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        except Exception as email_error:
            print(f"Failed to send approval email: {email_error}")
            # Continue even if email fails
        
        return jsonify({'message': 'Order approved successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@order_bp.route('/reject-order/<string:order_id>', methods=['DELETE'])
@token_required(roles=['admin'])
def reject_order(order_id):
    try:
        # Fetch the order
        order = Order.query.filter_by(order_id=order_id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Fetch the customer
        customer = None
        if order.customer_id:
            customer = Customer.query.get(order.customer_id)
        elif order.offline_customer_id:
            # Handle offline customer logic if applicable
            pass

        if not customer:
            return jsonify({'error': 'Customer not found'}), 404

        # Update order status to REJECTED (soft delete)
        order.order_status = "REJECTED"
        db.session.commit()

        # Send rejection email to customer
        try:
            subject = f"Your Order #{order_id} Has Been Rejected"
            body = f"""
            Dear {customer.name},
            
            We regret to inform you that your order #{order_id} has been rejected.
            
            Order Details:
            - Order ID: {order_id}
            - Total Amount: {order.total_amount}
            - Status: Rejected
            
            If you believe this was a mistake or have any questions, please contact our support team.
            
            Best regards,
            Your Store Team
            """
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = SMTP_USERNAME
            msg['To'] = customer.email

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        except Exception as email_error:
            print(f"Failed to send rejection email: {email_error}")
            # Continue even if email fails

        return jsonify({'message': 'Order rejected successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500




@order_bp.route('/update-payment-status/<path:order_id>', methods=['PUT'])
@token_required(roles=['admin'])
def update_payment_status(order_id):
    try:
        data = request.get_json()
        payment_status = data.get('payment_status')

        if not payment_status:
            return jsonify({'error': 'payment_status is required'}), 400

        order = Order.query.filter_by(order_id=order_id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        order.payment_status = payment_status
        db.session.commit()

        return jsonify({'message': 'Payment status updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    

@order_bp.route('/update-order-status/<string:order_id>', methods=['PUT'])
@token_required(roles=['admin'])
def update_order_status(order_id):
    try:
        print(f"Received update request for order: {order_id}")  # Debug log
        
        data = request.get_json()
        action = data.get('action')  # 'fulfill', 'shipped', or 'delivered'
        
        if not action or action not in ['fulfill', 'shipped', 'delivered']:
            return jsonify({'error': 'Invalid action. Must be fulfill, shipped, or delivered'}), 400

        # No need to decode here - Flask automatically handles URL-safe characters
        order = Order.query.filter_by(order_id=order_id).first()
        if not order:
            print(f"Order {order_id} not found in database")
            return jsonify({'error': 'Order not found'}), 404

        # Track previous values
        prev_fulfillment = order.fulfillment_status
        prev_delivery = order.delivery_status

        # Status transition logic
        if action == 'fulfill':
            if order.fulfillment_status:
                return jsonify({'message': 'Order is already fulfilled'}), 200
            order.fulfillment_status = True
            order.delivery_status = 'processing'  # Initial status after fulfillment

        elif action == 'shipped':
            if not order.fulfillment_status:
                return jsonify({'error': 'Order must be fulfilled before shipping'}), 400
            if order.delivery_status == 'shipped':
                return jsonify({'message': 'Order is already shipped'}), 200
            order.delivery_status = 'shipped'

        elif action == 'delivered':
            if order.delivery_status != 'shipped':
                return jsonify({'error': 'Order must be shipped before marking as delivered'}), 400
            order.delivery_status = 'delivered'

        # Create status history record
        status_history = OrderStatusHistory(
            order_id=order.order_id,
            changed_by='admin',  
            from_status=f"fulfill:{prev_fulfillment}, delivery:{prev_delivery}",
            to_status=f"fulfill:{order.fulfillment_status}, delivery:{order.delivery_status}",
            change_reason=f"Status updated via {action} action"
        )
        db.session.add(status_history)
        
        order.updated_at = datetime.now(tz=ZoneInfo('Asia/Kolkata'))
        db.session.commit()

        return jsonify({
            'message': f'Order status updated successfully',
            'order_id': order.order_id,
            'fulfillment_status': order.fulfillment_status,
            'delivery_status': order.delivery_status,
            'updated_at': order.updated_at.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating order {order_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@order_bp.route('/order/<string:order_id>/track',methods=['GET'])
@token_required(roles=['customer', 'admin']) 
def track_order(order_id):

       try:
           order = Order.query.filter_by(order_id=order_id).first()
           if not order:
               return jsonify({'error': 'Order not found'}), 404
           waybill=order.awb_number
           if not waybill:
               return jsonify({'error': 'Waybill not found'}), 404
           # Call the API to track the order
           
           DELHIVERY_KEY = os.getenv("DELHIVERY_KEY")
           url = f"https://track.delhivery.com/api/v1/packages/json/?waybill={waybill}&token={DELHIVERY_KEY}"

           response = requests.get(url)
           data = response.json()
           shipment_status = data.get("ShipmentData", [{}])[0].get("Shipment", {}).get("Status", {}).get("Status", "")
           print(shipment_status)
           if shipment_status == 'In Transit':
                order.delivery_status = 'Shipped'
           elif shipment_status == 'Delivered':
               order.delivery_status = 'Delivered'
           db.session.add(order)
           db.session.commit()
           return jsonify(data)
       
       except requests.exceptions.RequestException as e:
        return {'error': str(e)}



@order_bp.route('/order/<string:order_id>/get-all-info', methods=['GET'])
def get_order_details(order_id):
    """
    Get comprehensive details about a specific order by order_id
    
    Returns all information related to the order including:
    - Order basic info
    - Customer details
    - Address details
    - Order items with product information
    - Serial numbers for each item
    - Order status history
    """
    # Find the order
    order = Order.query.filter_by(order_id=order_id).first()
    
    if not order:
        return jsonify({
            'success': False,
            'message': f'Order with ID {order_id} not found'
        }), 404
    
    # Get customer information
    customer_info = {}
    if order.customer_id:
        customer = Customer.query.get(order.customer_id)
        if customer:
            customer_info = {
                'type': 'online',
                'customer_id': customer.customer_id,
                'name': customer.name,
                'email': customer.email,
                'mobile': customer.mobile,
                'role': customer.role,
                'gender': customer.gender,
                'age': customer.age,
                'created_at': customer.created_at.isoformat() if hasattr(customer, 'created_at') and customer.created_at else None
            }
    elif order.offline_customer_id:
        offline_customer = OfflineCustomer.query.get(order.offline_customer_id)
        if offline_customer:
            customer_info = {
                'type': 'offline',
                'customer_id': offline_customer.customer_id,
                'name': offline_customer.name,
                'email': offline_customer.email,
                'mobile': offline_customer.mobile,
                'role': offline_customer.role,
                'created_at': offline_customer.created_at.isoformat() if hasattr(offline_customer, 'created_at') and offline_customer.created_at else None
            }
    
    # Get address information
    address_info = {}
    if order.address_id:
        address = Address.query.get(order.address_id)
        if address:
            address_info = {
                'address_id': address.address_id,
                'name': address.name,
                'mobile': address.mobile,
                'pincode': address.pincode,
                'locality': address.locality,
                'address_line': address.address_line,
                'city': address.city,
                'state_id': address.state_id,
                'state_name': address.state.name if address.state else None,
                'landmark': address.landmark,
                'alternate_phone': address.alternate_phone,
                'address_type': address.address_type,
                'latitude': address.latitude,
                'longitude': address.longitude
            }
    
    # Get order items with product details and serial numbers
    items_info = []
    for item in order.items:
        # Get product details
        product_info = {}
        if item.product:
            product_info = {
                'product_id': item.product.product_id,
                'name': item.product.name,
                'description': item.product.description,
                'product_type': item.product.product_type,
                'rating': item.product.rating,
                'raters': item.product.raters,
                'sku_id': item.product.sku_id,
                'category_id': item.product.category_id
            }
            
            # Get product images
            product_images = []
            if hasattr(item.product, 'images'):
                product_images = [img.image_url for img in item.product.images]
            product_info['images'] = product_images
            
            # Get product specifications
            product_specs = {}
            if hasattr(item.product, 'specifications'):
                for spec in item.product.specifications:
                    product_specs[spec.key] = spec.value
            product_info['specifications'] = product_specs
        
        # Get model details
        model_info = {}
        if item.model:
            model_info = {
                'model_id': item.model.model_id,
                'name': item.model.name,
                'description': item.model.description
            }
            
            # Get model specifications
            model_specs = {}
            if hasattr(item.model, 'specifications'):
                for spec in item.model.specifications:
                    model_specs[spec.key] = spec.value
            model_info['specifications'] = model_specs
        
        # Get color details
        color_info = {}
        if item.color:
            color_info = {
                'color_id': item.color.color_id,
                'name': item.color.name,
                'price': float(item.color.price) if hasattr(item.color, 'price') and item.color.price is not None else None,
                'original_price': float(item.color.original_price) if hasattr(item.color, 'original_price') and item.color.original_price is not None else None,
                'stock_quantity': item.color.stock_quantity if hasattr(item.color, 'stock_quantity') else None
            }
            
            # Get color images
            color_images = []
            if hasattr(item.color, 'images'):
                color_images = [img.image_url for img in item.color.images]
            color_info['images'] = color_images
        
        # Get serial numbers
        serial_numbers = []
        if hasattr(item, 'serial_numbers'):
            serial_numbers = [
                {
                    'id': sn.id,
                    'sr_number': sn.sr_number
                } for sn in item.serial_numbers
            ]
        
        # Get item details
        item_details = []
        if hasattr(item, 'details'):
            item_details = [
                {
                    'id': detail.id,
                    'sr_no': detail.sr_no
                } for detail in item.details
            ]
        
        # Combine all item information
        items_info.append({
            'item_id': item.item_id if hasattr(item, 'item_id') else None,
            'product': product_info,
            'model': model_info,
            'color': color_info,
            'quantity': item.quantity if hasattr(item, 'quantity') else None,
            'unit_price': float(item.unit_price) if hasattr(item, 'unit_price') and item.unit_price is not None else None,
            'total_price': float(item.total_price) if hasattr(item, 'total_price') and item.total_price is not None else None,
            'serial_numbers': serial_numbers,
            'details': item_details
        })
    
    # Get order status history
    status_history = []
    if hasattr(order, 'status_history'):
        status_history = [
            {
                'id': record.id,
                'changed_by': record.changed_by if hasattr(record, 'changed_by') else None,
                'from_status': record.from_status if hasattr(record, 'from_status') else None,
                'to_status': record.to_status if hasattr(record, 'to_status') else None,
                'change_reason': record.change_reason if hasattr(record, 'change_reason') else None,
                'changed_at': record.changed_at.isoformat() if hasattr(record, 'changed_at') and record.changed_at else None
            } for record in order.status_history
        ]
    
    # Create the response with all order information
    response = {
        'success': True,
        'data': {
            'order': {
                'order_id': order.order_id,
                'order_index': order.order_index if hasattr(order, 'order_index') else None,
                'total_items': order.total_items if hasattr(order, 'total_items') else None,
                'subtotal': float(order.subtotal) if order.subtotal is not None else None,
                'discount_percent': float(order.discount_percent) if order.discount_percent is not None else None,
                'delivery_charge': float(order.delivery_charge) if order.delivery_charge is not None else None,
                'tax_percent': float(order.tax_percent) if order.tax_percent is not None else None,
                'total_amount': float(order.total_amount) if order.total_amount is not None else None,
                'channel': order.channel if hasattr(order, 'channel') else None,
                'payment_status': order.payment_status if hasattr(order, 'payment_status') else None,
                'fulfillment_status': order.fulfillment_status if hasattr(order, 'fulfillment_status') else None,
                'delivery_status': order.delivery_status if hasattr(order, 'delivery_status') else None,
                'delivery_method': order.delivery_method if hasattr(order, 'delivery_method') else None,
                'awb_number': order.awb_number if hasattr(order, 'awb_number') else None,
                'upload_wbn': order.upload_wbn if hasattr(order, 'upload_wbn') else None,
                'order_status': order.order_status if hasattr(order, 'order_status') else None,
                'payment_type': order.payment_type if hasattr(order, 'payment_type') else None,
                'gst': float(order.gst) if order.gst is not None else None,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'updated_at': order.updated_at.isoformat() if order.updated_at else None
            },
            'customer': customer_info,
            'address': address_info,
            'items': items_info,
            'status_history': status_history
        }
    }
    
    return jsonify(response), 200



@order_bp.route('/order/by-serial-number/<string:sr_number>', methods=['GET'])
def get_order_details_by_sr_number(sr_number):
    """
    Get comprehensive details about a specific order by serial number (sr_number)
    
    Returns all information related to the order including:
    - Order basic info
    - Customer details
    - Address details
    - Order items with product information
    - Serial numbers for each item
    - Order status history
    """
    # Find serial number in database
    serial_number = SerialNumber.query.filter_by(sr_number=sr_number).first()
    
    if not serial_number:
        # Try checking if it's in order details
        order_detail = OrderDetail.query.filter_by(sr_no=sr_number).first()
        if not order_detail:
            return jsonify({
                'success': False,
                'message': f'No order found with serial number {sr_number}'
            }), 404
        
        # Get order from order detail
        order_id = order_detail.order_id
    else:
        # Get order_id from serial number via order item
        order_id = serial_number.order_item.order_id
    
    # Find the order
    order = Order.query.filter_by(order_id=order_id).first()
    
    if not order:
        return jsonify({
            'success': False,
            'message': f'Order with ID {order_id} not found'
        }), 404
    
    # Get customer information
    customer_info = {}
    if order.customer_id:
        customer = Customer.query.get(order.customer_id)
        if customer:
            customer_info = {
                'type': 'online',
                'customer_id': customer.customer_id,
                'name': customer.name,
                'email': customer.email,
                'mobile': customer.mobile,
                'role': customer.role,
                'gender': customer.gender,
                'age': customer.age,
                'created_at': customer.created_at.isoformat() if hasattr(customer, 'created_at') and customer.created_at else None
            }
    elif order.offline_customer_id:
        offline_customer = OfflineCustomer.query.get(order.offline_customer_id)
        if offline_customer:
            customer_info = {
                'type': 'offline',
                'customer_id': offline_customer.customer_id,
                'name': offline_customer.name,
                'email': offline_customer.email,
                'mobile': offline_customer.mobile,
                'role': offline_customer.role,
                'created_at': offline_customer.created_at.isoformat() if hasattr(offline_customer, 'created_at') and offline_customer.created_at else None
            }
    
    # Get address information
    address_info = {}
    if order.address_id:
        address = Address.query.get(order.address_id)
        if address:
            address_info = {
                'address_id': address.address_id,
                'name': address.name,
                'mobile': address.mobile,
                'pincode': address.pincode,
                'locality': address.locality,
                'address_line': address.address_line,
                'city': address.city,
                'state_id': address.state_id,
                'state_name': address.state.name if address.state else None,
                'landmark': address.landmark,
                'alternate_phone': address.alternate_phone,
                'address_type': address.address_type,
                'latitude': address.latitude,
                'longitude': address.longitude
            }
    
    # Get order items with product details and serial numbers
    items_info = []
    for item in order.items:
        # Get product details
        product_info = {}
        if item.product:
            product_info = {
                'product_id': item.product.product_id,
                'name': item.product.name,
                'description': item.product.description,
                'product_type': item.product.product_type,
                'rating': item.product.rating,
                'raters': item.product.raters,
                'sku_id': item.product.sku_id,
                'category_id': item.product.category_id
            }
            
            # Get product images
            product_images = []
            if hasattr(item.product, 'images'):
                product_images = [img.image_url for img in item.product.images]
            product_info['images'] = product_images
            
            # Get product specifications
            product_specs = {}
            if hasattr(item.product, 'specifications'):
                for spec in item.product.specifications:
                    product_specs[spec.key] = spec.value
            product_info['specifications'] = product_specs
        
        # Get model details
        model_info = {}
        if item.model:
            model_info = {
                'model_id': item.model.model_id,
                'name': item.model.name,
                'description': item.model.description
            }
            
            # Get model specifications
            model_specs = {}
            if hasattr(item.model, 'specifications'):
                for spec in item.model.specifications:
                    model_specs[spec.key] = spec.value
            model_info['specifications'] = model_specs
        
        # Get color details
        color_info = {}
        if item.color:
            color_info = {
                'color_id': item.color.color_id,
                'name': item.color.name,
                'price': float(item.color.price) if hasattr(item.color, 'price') and item.color.price is not None else None,
                'original_price': float(item.color.original_price) if hasattr(item.color, 'original_price') and item.color.original_price is not None else None,
                'stock_quantity': item.color.stock_quantity if hasattr(item.color, 'stock_quantity') else None
            }
            
            # Get color images
            color_images = []
            if hasattr(item.color, 'images'):
                color_images = [img.image_url for img in item.color.images]
            color_info['images'] = color_images
        
        # Get serial numbers
        serial_numbers = []
        if hasattr(item, 'serial_numbers'):
            serial_numbers = [
                {
                    'id': sn.id,
                    'sr_number': sn.sr_number
                } for sn in item.serial_numbers
            ]
        
        # Get item details
        item_details = []
        if hasattr(item, 'details'):
            item_details = [
                {
                    'id': detail.id,
                    'sr_no': detail.sr_no
                } for detail in item.details
            ]
        
        # Combine all item information
        items_info.append({
            'item_id': item.item_id if hasattr(item, 'item_id') else None,
            'product': product_info,
            'model': model_info,
            'color': color_info,
            'quantity': item.quantity if hasattr(item, 'quantity') else None,
            'unit_price': float(item.unit_price) if hasattr(item, 'unit_price') and item.unit_price is not None else None,
            'total_price': float(item.total_price) if hasattr(item, 'total_price') and item.total_price is not None else None,
            'serial_numbers': serial_numbers,
            'details': item_details
        })
    
    # Get order status history
    status_history = []
    if hasattr(order, 'status_history'):
        status_history = [
            {
                'id': record.id,
                'changed_by': record.changed_by if hasattr(record, 'changed_by') else None,
                'from_status': record.from_status if hasattr(record, 'from_status') else None,
                'to_status': record.to_status if hasattr(record, 'to_status') else None,
                'change_reason': record.change_reason if hasattr(record, 'change_reason') else None,
                'changed_at': record.changed_at.isoformat() if hasattr(record, 'changed_at') and record.changed_at else None
            } for record in order.status_history
        ]
    
    # Create the response with all order information
    response = {
        'success': True,
        'data': {
            'order': {
                'order_id': order.order_id,
                'order_index': order.order_index if hasattr(order, 'order_index') else None,
                'total_items': order.total_items if hasattr(order, 'total_items') else None,
                'subtotal': float(order.subtotal) if order.subtotal is not None else None,
                'discount_percent': float(order.discount_percent) if order.discount_percent is not None else None,
                'delivery_charge': float(order.delivery_charge) if order.delivery_charge is not None else None,
                'tax_percent': float(order.tax_percent) if order.tax_percent is not None else None,
                'total_amount': float(order.total_amount) if order.total_amount is not None else None,
                'channel': order.channel if hasattr(order, 'channel') else None,
                'payment_status': order.payment_status if hasattr(order, 'payment_status') else None,
                'fulfillment_status': order.fulfillment_status if hasattr(order, 'fulfillment_status') else None,
                'delivery_status': order.delivery_status if hasattr(order, 'delivery_status') else None,
                'delivery_method': order.delivery_method if hasattr(order, 'delivery_method') else None,
                'awb_number': order.awb_number if hasattr(order, 'awb_number') else None,
                'upload_wbn': order.upload_wbn if hasattr(order, 'upload_wbn') else None,
                'order_status': order.order_status if hasattr(order, 'order_status') else None,
                'payment_type': order.payment_type if hasattr(order, 'payment_type') else None,
                'gst': float(order.gst) if order.gst is not None else None,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'updated_at': order.updated_at.isoformat() if order.updated_at else None
            },
            'customer': customer_info,
            'address': address_info,
            'items': items_info,
            'status_history': status_history,
            'searched_serial_number': sr_number
        }
    }
    
    return jsonify(response), 200

