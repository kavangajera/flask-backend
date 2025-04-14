# from flask import Blueprint, request, jsonify
# from models.order import OrderHistory, OrderHistoryItem
# from models.cart import Cart,CartItem
# from models.product import Product,ProductColor,ProductModel,ProductSpecification,ModelSpecification
# import decimal
# from extensions import db
# from middlewares.auth import token_required

# order_bp = Blueprint('order', __name__)


# @order_bp.route('/cart/additem', methods=['POST'])
# @token_required(roles=['customer'])
# def add_item_to_cart():
#     data = request.json
#     data = request.get_json()
    
#     # Validate request data
#     required_fields = ['product_id']
#     for field in required_fields:
#         if field not in data:
#             return jsonify({'error': f'Missing required field: {field}'}), 400
    
#     product_id = data.get('product_id')
#     model_id = data.get('model_id')
#     color_id = data.get('color_id')
#     spec_id = data.get('spec_id')
#     quantity = data.get('quantity', 1)
    
#     # Fetch the product to check if it exists and get the price
#     product = Product.query.get(product_id)
#     if not product:
#         return jsonify({'error': 'Product not found'}), 404
    
#     # Get the price from the product color if color_id is provided
#     # Otherwise use the product's base price (for single products)
#     if color_id:
#         product_color = ProductColor.query.get(color_id)
#         if not product_color:
#             return jsonify({'error': 'Product color not found'}), 404
#         price = product_color.price
#     else:
#         # Assuming single products have a base price
#         # You might need to adjust this logic based on your actual product model
#         return jsonify({'error': 'Color ID is required'}), 400
    
#     # Calculate the total price for this item
#     total_item_price = decimal.Decimal(price) * decimal.Decimal(quantity)
    
#     # Check if the user already has a cart, if not create one
#     cart = Cart.query.filter_by(customer_id=request.current_user.customer_id).first()
#     if not cart:
#         cart = Cart(customer_id=request.current_user.customer_id)
#         db.session.add(cart)
#         db.session.flush()  # Flush to get the cart_id without committing
    
#     # Check if the item already exists in the cart
#     existing_item = CartItem.query.filter_by(
#         cart_id=cart.cart_id,
#         product_id=product_id,
#         model_id=model_id,
#         color_id=color_id,
#         spec_id=spec_id
#     ).first()
    
#     if existing_item:
#         # Update existing item quantity and price
#         existing_item.quantity += quantity
#         existing_item.total_item_price = decimal.Decimal(existing_item.quantity) * decimal.Decimal(price)
#     else:
#         # Create new cart item
#         cart_item = CartItem(
#             cart_id=cart.cart_id,
#             product_id=product_id,
#             model_id=model_id,
#             color_id=color_id,
#             spec_id=spec_id,
#             quantity=quantity,
#             total_item_price=total_item_price
#         )
#         db.session.add(cart_item)
    
#     # Update the cart's total price
#     cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
#     cart.total_cart_price = sum(decimal.Decimal(item.total_item_price) for item in cart_items)
    
#     # Commit all changes
#     db.session.commit()
    
#     return jsonify({
#         'success': True,
#         'message': 'Item added to cart successfully',
#         'cart_id': cart.cart_id,
#         'total_cart_price': float(cart.total_cart_price)
#     }), 200



# # Delete Item:
# @order_bp.route('/cart/deleteitem', methods=['POST'])
# @token_required(roles=['customer'])
# def delete_item_from_cart():
#     data = request.get_json()
    
#     # Validate request data
#     required_fields = ['product_id']
#     for field in required_fields:
#         if field not in data:
#             return jsonify({'error': f'Missing required field: {field}'}), 400
    
#     product_id = data.get('product_id')
#     model_id = data.get('model_id')
#     color_id = data.get('color_id')
#     spec_id = data.get('spec_id')
#     quantity_to_remove = data.get('quantity', 1)
    
#     # Check if the user has a cart
#     cart = Cart.query.filter_by(customer_id=request.current_user.customer_id).first()
#     if not cart:
#         return jsonify({'error': 'No cart found for this user'}), 404
    
#     # Find the cart item using product details
#     query = CartItem.query.filter_by(
#         cart_id=cart.cart_id,
#         product_id=product_id
#     )
    
#     # Add optional filters if they were provided
#     if model_id is not None:
#         query = query.filter_by(model_id=model_id)
#     if color_id is not None:
#         query = query.filter_by(color_id=color_id)
#     if spec_id is not None:
#         query = query.filter_by(spec_id=spec_id)
    
#     cart_item = query.first()
    
#     if not cart_item:
#         return jsonify({'error': 'Item not found in cart'}), 404
    
#     # If quantity to remove is less than current quantity, just reduce quantity
#     if quantity_to_remove < cart_item.quantity:
#         cart_item.quantity -= quantity_to_remove
        
#         # Recalculate the item price
#         # Get the price from the product color
#         if cart_item.color_id:
#             product_color = ProductColor.query.get(cart_item.color_id)
#             if not product_color:
#                 return jsonify({'error': 'Product color not found'}), 500
#             price = product_color.price
#         else:
#             # This should not happen based on your model, but just in case
#             return jsonify({'error': 'Color ID is required'}), 500
        
#         # Update item price
#         cart_item.total_item_price = decimal.Decimal(cart_item.quantity) * decimal.Decimal(price)
#     else:
#         # Remove the entire cart item
#         db.session.delete(cart_item)
    
#     # Recalculate the cart's total price
#     # Get all remaining items after the current session changes
#     db.session.flush()
#     remaining_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
    
#     if remaining_items:
#         cart.total_cart_price = sum(decimal.Decimal(item.total_item_price) for item in remaining_items)
#     else:
#         cart.total_cart_price = 0
    
#     # Commit all changes
#     db.session.commit()
    
#     return jsonify({
#         'success': True,
#         'message': 'Item removed from cart successfully',
#         'cart_id': cart.cart_id,
#         'total_cart_price': float(cart.total_cart_price)
#     }), 200




# @order_bp.route('/cart/getbycustid' , methods=['GET'])
# @token_required(roles=['customer'])
# def get_cart_by_customer_id():

#     customer_id=request.current_user.customer_id
#     cart = Cart.query.filter_by(customer_id=customer_id).first()
    
#     if not cart:
#         return jsonify({
#             'success': True,
#             'cart': {
#                 'cart_id': None,
#                 'customer_id': customer_id,
#                 'total_price': 0,
#                 'items': [],
#                 'item_count': 0
#             }
#         }), 200
    
#     # Get all items in the cart with detailed information
#     cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
    
#     items_list = []
#     for item in cart_items:
#         # Get product details
#         product = Product.query.get(item.product_id)
        
#         # Get model details if applicable
#         model = None
#         if item.model_id:
#             model = ProductModel.query.get(item.model_id)
        
#         # Get color details if applicable
#         color = None
#         if item.color_id:
#             color = ProductColor.query.get(item.color_id)
        
#         # Get product specification details if applicable
#         product_specifications = []
#         if product:
#             prod_specs = ProductSpecification.query.filter_by(product_id=product.product_id).all()
#             for spec in prod_specs:
#                 product_specifications.append({
#                     'spec_id': spec.spec_id,
#                     'key': spec.key,
#                     'value': spec.value
#                 })
        
#         # Get model specification details if applicable
#         model_specifications = []
#         if model:
#             mod_specs = ModelSpecification.query.filter_by(model_id=model.model_id).all()
#             for spec in mod_specs:
#                 model_specifications.append({
#                     'spec_id': spec.spec_id,
#                     'key': spec.key,
#                     'value': spec.value
#                 })
        
#         # Get product image (first one if available)
#         product_image = None
#         if product and hasattr(product, 'images') and product.images:
#             product_image = product.images[0].image_url if product.images else None
        
#         # Get color-specific image if available
#         color_image = None
#         if color and hasattr(color, 'images') and color.images:
#             color_image = color.images[0].image_url if color.images else None
        
#         # Construct detailed item information
#         item_details = {
#             'item_id': item.item_id,
#             'product': {
#                 'product_id': product.product_id if product else None,
#                 'name': product.name if product else 'Unknown',
#                 'description': product.description if product else None,
#                 'product_type': product.product_type if product else None,
#                 'rating': float(product.rating) if product and product.rating else 0,
#                 'image_url': color_image or product_image,
#                 'specifications': product_specifications
#             },
#             'model': {
#                 'model_id': model.model_id if model else None,
#                 'name': model.name if model else None,
#                 'description': model.description if model else None,
#                 'specifications': model_specifications
#             } if model else None,
#             'color': {
#                 'color_id': color.color_id if color else None,
#                 'name': color.name if color else None,
#                 'price': float(color.price) if color else None,
#                 'original_price': float(color.original_price) if color and color.original_price else None,
#                 'stock_quantity': color.stock_quantity if color else None
#             } if color else None,
#             'quantity': item.quantity,
#             'unit_price': float(item.total_item_price / item.quantity) if item.quantity > 0 else 0,
#             'total_item_price': float(item.total_item_price),
#             'added_at': item.added_at.isoformat() if hasattr(item, 'added_at') and item.added_at else None
#         }
        
#         items_list.append(item_details)
    
#     # Calculate any potential discounts
#     # This is a placeholder - implement your discount logic here
#     subtotal = float(cart.total_cart_price)
#     discount = 0  # Calculate any applicable discounts
#     tax = 0  # Calculate any applicable taxes
#     shipping = 0  # Calculate shipping costs
#     total = subtotal - discount + tax + shipping
    
#     response = {
#         'success': True,
#         'cart': {
#             'cart_id': cart.cart_id,
#             'customer_id': customer_id,
#             'created_at': cart.created_at.isoformat() if hasattr(cart, 'created_at') and cart.created_at else None,
#             'updated_at': cart.updated_at.isoformat() if hasattr(cart, 'updated_at') and cart.updated_at else None,
#             'item_count': len(items_list),
#             'items': items_list,
#             'pricing': {
#                 'subtotal': subtotal,
#                 'discount': discount,
#                 'tax': tax,
#                 'shipping': shipping,
#                 'total': total
#             }
#         }
#     }
    
#     return jsonify(response), 200
    


# @order_bp.route('/cart/clear', methods=['DELETE'])
# @token_required(roles=['customer'])
# def clear_cart():
#     # Get the customer's cart
#     customer_id=request.current_user.customer_id
#     cart = Cart.query.filter_by(customer_id=customer_id).first()
    
#     if not cart:
#         return jsonify({
#             'success': True,
#             'message': 'Cart is already empty'
#         }), 200
    
#     # Delete all items in the cart
#     CartItem.query.filter_by(cart_id=cart.cart_id).delete()
    
#     # Reset cart total
#     cart.total_cart_price = 0
    
#     db.session.commit()
    
#     return jsonify({
#         'success': True,
#         'message': 'Cart cleared successfully'
#     }), 200


# @order_bp.route('/orders', methods=['GET'])
# @token_required(roles=['customer'])
# def list_orders():
#     orders = OrderHistory.query.filter_by(customer_id=request.current_user.customer_id).all()
#     orders_list = []
#     for order in orders:
#         order_dict = {
#             'order_id': order.order_id,
#             'customer_id': order.customer_id,
#             'address': order.address,
#             'date_time': order.date_time.isoformat() if order.date_time else None,
#             'num_products': order.num_products,
#             'total_price': float(order.total_price) if order.total_price else None,
#             'delivery_charge': float(order.delivery_charge) if order.delivery_charge else None,
#             'final_payment': float(order.final_payment) if order.final_payment else None,
#             'items': []
#         }
#         for item in order.items:
#             item_dict = {
#                 'item_id': item.item_id,
#                 'product_id': item.product_id,
#                 'quantity': item.quantity,
#                 'product_price': float(item.product_price) if item.product_price else None
#             }
#             order_dict['items'].append(item_dict)
#         orders_list.append(order_dict)
#     return jsonify(orders_list)

# @order_bp.route('/order/create', methods=['POST'])
# @token_required(roles=['customer'])
# def create_order():
#     data = request.get_json()
#     current_user = request.current_user
#     if not data or 'items' not in data:
#         return jsonify({'error': 'No items provided'}), 400
    
#     try:
#         # Calculate order totals
#         total_price = 0
#         num_products = len(data['items'])
        
#         # Create new order
#         new_order = OrderHistory(
#             customer_id=request.current_user.customer_id,
#             address=data.get('address'),
#             num_products=num_products,
#             total_price=0,  # Will be updated after items
#             delivery_charge=data.get('delivery_charge', 0),
#             final_payment=0  # Will be updated after items
#         )
        
#         db.session.add(new_order)
#         db.session.flush()  # Get the order_id
        
#         # Add order items
#         for item_data in data['items']:
#             item = OrderHistoryItem(
#                 order_id=new_order.order_id,
#                 product_id=item_data['product_id'],
#                 quantity=item_data['quantity'],
#                 product_price=item_data['product_price']
#             )
#             db.session.add(item)
#             total_price += float(item_data['product_price']) * item_data['quantity']
        
#         # Update order totals
#         new_order.total_price = total_price
#         new_order.final_payment = total_price + float(new_order.delivery_charge or 0)
        
#         db.session.commit()
        
#         return jsonify({
#             'message': 'Order created successfully',
#             'order_id': new_order.order_id
#         }), 201
        
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 400

# @order_bp.route('/order/<int:order_id>', methods=['GET'])
# @token_required(roles=['customer'])
# def get_order(order_id):
#     current_user = request.current_user
#     order = OrderHistory.query.filter_by(
#         order_id=order_id,
#         customer_id=request.current_user.customer_id
#     ).first_or_404()
    
#     order_dict = {
#         'order_id': order.order_id,
#         'customer_id': order.customer_id,
#         'address': order.address,
#         'date_time': order.date_time.isoformat() if order.date_time else None,
#         'num_products': order.num_products,
#         'total_price': float(order.total_price) if order.total_price else None,
#         'delivery_charge': float(order.delivery_charge) if order.delivery_charge else None,
#         'final_payment': float(order.final_payment) if order.final_payment else None,
#         'items': []
#     }
    
#     for item in order.items:
#         item_dict = {
#             'item_id': item.item_id,
#             'product_id': item.product_id,
#             'quantity': item.quantity,
#             'product_price': float(item.product_price) if item.product_price else None
#         }
#         order_dict['items'].append(item_dict)
    
#     return jsonify(order_dict) 

from flask import Blueprint, request, jsonify
from models.order import OrderHistory, OrderHistoryItem
from models.cart import Cart,CartItem
from models.product import Product,ProductColor,ProductModel,ModelSpecification
import decimal
from extensions import db
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
        # query = query.filter_by(spec_id=spec_id)
    
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
        
       
       
        
        # Get model specification details if applicable
        model_specifications = []
        if model:
            mod_specs = ModelSpecification.query.filter_by(model_id=model.model_id).all()
            for spec in mod_specs:
                model_specifications.append({
                    # 'spec_id': spec.spec_id,
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
                'specifications': model_specifications
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
@token_required(roles=['customer'])
def list_orders():
    orders = OrderHistory.query.filter_by(customer_id=request.current_user.customer_id).all()
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
@token_required(roles=['customer'])
def create_order():
    data = request.get_json()
    current_user = request.current_user
    if not data or 'items' not in data:
        return jsonify({'error': 'No items provided'}), 400
    
    try:
        # Calculate order totals
        total_price = 0
        num_products = len(data['items'])
        
        # Create new order
        new_order = OrderHistory(
            customer_id=request.current_user.customer_id,
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
@token_required(roles=['customer'])
def get_order(order_id):
    current_user = request.current_user
    order = OrderHistory.query.filter_by(
        order_id=order_id,
        customer_id=request.current_user.customer_id
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
