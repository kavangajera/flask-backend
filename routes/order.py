from flask import Blueprint, request, jsonify
from models.order import Order,OrderItem,OrderDetail
from models.offline_customer import OfflineCustomer
from models.cart import Cart,CartItem
from models.product import Product,ProductColor,ProductModel,ModelSpecification,ProductSpecification
from models.address import Address
from models.device import DeviceTransaction
import decimal
from extensions import db
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime


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
    spec_id = data.get('spec_id')
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
            price = color.price if color else product.price
        else:
            price = product.price
    
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
        spec_id=spec_id
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
            spec_id=spec_id,
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
    spec_id = data.get('spec_id')
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
    if spec_id is not None:
        query = query.filter_by(spec_id=spec_id)
    
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
            'longitude': order.address.longitude
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
        'created_at': order.created_at.isoformat(),
        'items': [{
            'product_id': item.product_id,
            'model_id': item.model_id,
            'color_id': item.color_id,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'total_price': float(item.total_price)
        } for item in order.items]
    } for order in orders])


def generate_order_id():
    """
    Generates order ID in format YYYY(CurrentYear)YY(NextYear)#SequenceNumber
    Example: For year 2025 → '202526#1', '202526#2', etc.
    """
    current_year = datetime.now().year
    next_year = current_year + 1
    
    # Format: Full current year + last 2 digits of next year
    year_part = f"{current_year}{next_year % 100:02d}"
    
    # Find the highest existing sequence number for this year pattern
    last_order = Order.query.filter(
        Order.order_id.like(f"{year_part}#%")
    ).order_by(Order.order_id.desc()).first()
    
    if last_order:
        try:
            # Extract the number after # and increment
            last_num = int(last_order.order_id.split('#')[1])
            sequence_num = last_num + 1
        except (IndexError, ValueError):
            # Fallback if format is corrupted
            sequence_num = 1
    else:
        sequence_num = 1
    
    return f"{year_part}#{sequence_num}"




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

        unit_price = color.price if color else product.price
        total_price = unit_price * item['quantity']
        subtotal += total_price

        order_items.append({
            'product_id': item['product_id'],
            'model_id': item.get('model_id'),
            'color_id': item.get('color_id'),
            'quantity': item['quantity'],
            'unit_price': unit_price,
            'total_price': total_price
        })

        # Keep track of stock updates
        if color:
            color.stock_quantity -= item['quantity']
            stock_updates.append(color)

    # Calculate totals
    discount_amount = (subtotal * data.get('discount_percent', 0)) / 100
    tax_amount = ((subtotal - discount_amount) * data.get('tax_percent', 0)) / 100
    total_amount = subtotal - discount_amount + tax_amount + data.get('delivery_charge', 0)

    order_id=generate_order_id()

    try:
        # Create and add order
        order = Order(
            order_id=order_id,
            offline_customer_id=customer.customer_id,
            address_id=address.address_id,
            total_items=len(order_items),
            subtotal=subtotal,
            discount_percent=data.get('discount_percent', 0),
            delivery_charge=data.get('delivery_charge', 0),
            tax_percent=data.get('tax_percent', 0),
            total_amount=total_amount,
            channel=data.get('channel', 'offline'),
            payment_status=data.get('payment_status', 'paid'),
            fulfillment_status=data.get('fulfillment_status', False),
            delivery_status=data.get('delivery_status', 'intransit'),
            delivery_method=data.get('delivery_method', 'shipping')
        )
        db.session.add(order)
        db.session.flush()  # So order_id is available for order items

        # Add order items and apply stock updates
        for item in order_items:
            order_item = OrderItem(
                order_id=order.order_id,
                product_id=item['product_id'],
                model_id=item['model_id'],
                color_id=item['color_id'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                total_price=item['total_price']
            )
            db.session.add(order_item)

        for color in stock_updates:
            db.session.add(color)
            if color.stock_quantity <= color.threshold:
                print(f"Warning: Product color {color.name} stock is below threshold ({color.stock_quantity}/{color.threshold})")

        db.session.commit()
        return jsonify({'message': 'Order created successfully', 'order_id': order.order_id}), 201

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
    subtotal = float(cart.total_cart_price)
    discount_percent = data.get('discount_percent', 0)
    tax_percent = data.get('tax_percent', 0)
    delivery_charge = data.get('delivery_charge', 0)
    
    # Calculate final amount
    discount_amount = (subtotal * discount_percent) / 100
    tax_amount = ((subtotal - discount_amount) * tax_percent) / 100
    total_amount = subtotal - discount_amount + tax_amount + delivery_charge
    
    # Generate new order ID
    order_id = generate_order_id()
    
    # Create new order with custom ID
    order = Order(
        order_id=order_id,
        customer_id=customer_id,
        address_id=data['address_id'],
        total_items=len(cart_items),
        subtotal=subtotal,
        discount_percent=discount_percent,
        delivery_charge=delivery_charge,
        tax_percent=tax_percent,
        total_amount=total_amount,
        channel='online',  # Hardcoded for this endpoint
        payment_status=data['payment_status'],
        fulfillment_status=False,
        delivery_status='pending',
        delivery_method=data['delivery_method'],
        awb_number=data.get('awb_number'),
        created_at=datetime.now()
    )
    
    db.session.add(order)
    
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
            order_id=order_id,
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
                order_id=order_id,
                product_id=cart_item.product_id
            )
            db.session.add(order_detail)
        
        order_items.append(order_item)
    
    # Clear cart items
    for item in cart_items:
        db.session.delete(item)
    
    # Reset cart total
    cart.total_cart_price = 0
    
    try:
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Order placed successfully',
            'order': {
                'order_id': order_id,
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
            # Safely access related objects
            product_name = item.product.name if item.product and hasattr(item, 'product') else None
            model_name = item.model.name if item.model and hasattr(item, 'model') else None
            color_name = item.color.name if item.color and hasattr(item, 'color') else None
            
            for _ in range(item.quantity):
                expanded_items.append({
                    'item_id': item.item_id,
                    'product_id': item.product_id,
                    'model_id': item.model_id,
                    'color_id': item.color_id,
                    'unit_price': float(item.unit_price),
                    'total_price': float(item.unit_price),
                    'product_name': product_name,
                    'model_name': model_name,
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
            'delivery_status': order.delivery_status,
            'created_at': order.created_at.isoformat(),
            'items': expanded_items
        })
    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_order_items_expanded: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
    


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
            model_name = order_item.model.name if order_item.model and hasattr(order_item, 'model') else None
            color_name = order_item.color.name if order_item.color and hasattr(order_item, 'color') else None
            
            expanded_details.append({
                'detail_id': detail.id,
                'item_id': detail.item_id,
                'order_id': detail.order_id,
                'product_id': detail.product_id,
                'sr_no': detail.sr_no,
                'product_name': product_name,
                'model_name': model_name,
                'color_name': color_name,
                'unit_price': float(order_item.unit_price) if order_item else 0,
                'status': getattr(detail, 'status', None),  # Safely get status if it exists
                'created_at': detail.created_at.isoformat() if hasattr(detail, 'created_at') and detail.created_at else None
            })
        
        return jsonify({
            'order_id': order.order_id,
            'customer_id': order.customer_id,
            'total_details': len(expanded_details),
            'subtotal': float(order.subtotal),
            'total_amount': float(order.total_amount),
            'payment_status': order.payment_status,
            'fulfillment_status': order.fulfillment_status,
            'delivery_status': order.delivery_status,
            'created_at': order.created_at.isoformat(),
            'details': expanded_details
        })
    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_order_details_expanded: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500



# @order_bp.route('/orders/save-sr-numbers', methods=['POST'])
# def save_serial_numbers():
#     try:
#         data = request.get_json()
        
#         # Validate request data
#         if not data or not isinstance(data, list):
#             return jsonify({'error': 'Invalid request data format'}), 400
        
#         # Process each serial number
#         for sr_data in data:
#             # Find the order detail record
#             detail = OrderDetail.query.get(sr_data['detail_id'])
#             if not detail:
#                 continue  # Skip if detail not found
                
#             # Update the SR number only in OrderDetail
#             detail.sr_no = sr_data['sr_no']
#             db.session.add(detail)
        
#         db.session.commit()
        
#         return jsonify({
#             'success': True,
#             'message': 'Serial numbers saved successfully to OrderDetail'
#         })
        
#     except Exception as e:
#         db.session.rollback()
#         print(f"Error saving serial numbers: {str(e)}")
#         return jsonify({
#             'error': 'Failed to save serial numbers',
#             'details': str(e)
#         }), 500


@order_bp.route('/orders/save-sr-numbers', methods=['POST'])
def save_serial_numbers():
    try:
        data = request.get_json()
        
        # Validate request data
        if not data or not isinstance(data, list):
            return jsonify({'error': 'Invalid request data format'}), 400
        
        # Get order details first to get order information
        order_details = []
        for sr_data in data:
            detail = OrderDetail.query.get(sr_data['detail_id'])
            if not detail:
                continue
            order_details.append(detail)
        
        if not order_details:
            return jsonify({'error': 'No valid order details found'}), 400
        
        # Get the order from the first detail (all details should belong to the same order)
        order = order_details[0].order

        # Fallback SKU settings
        sku_prefix = 'sku'
        fallback_sku_counter = 123  # Starting point for fallback SKUs

        # Process each serial number
        for index, (sr_data, detail) in enumerate(zip(data, order_details)):
            sr_no = sr_data.get('sr_no')
            if not sr_no:
                continue  # Skip if no SR number provided
                
            # Update the SR number in OrderDetail
            detail.sr_no = sr_no
            db.session.add(detail)

            # Determine the SKU (with fallback)
            if detail.item and hasattr(detail.item, 'sku') and detail.item.sku:
                sku_id = detail.item.sku
            else:
                sku_id = f"{sku_prefix}{fallback_sku_counter + index}"

            # Create OUT transaction for this device
            transaction = DeviceTransaction(
                device_srno=sr_no,
                device_name=detail.item.product.name if detail.item and detail.item.product else 'Unknown Device',
                sku_id=sku_id,
                order_id=order.order_id,
                in_out=2,  # OUT transaction
                create_date=datetime.now().date(),
                price=float(detail.item.unit_price) if detail.item and hasattr(detail.item, 'unit_price') else None,
                remarks=f"Device sold in order {order.order_id}"
            )
            db.session.add(transaction)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Serial numbers saved successfully and OUT transactions created'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving serial numbers: {str(e)}")
        return jsonify({
            'error': 'Failed to save serial numbers',
            'details': str(e)
        }), 500

