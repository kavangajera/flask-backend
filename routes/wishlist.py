from flask import Blueprint, request, jsonify
from models.cart import Cart,CartItem
from models.product import Product,ProductColor,ProductModel,ModelSpecification
from models.wishlist import Wishlist,WishlistItem
import decimal
from extensions import db
from middlewares.auth import token_required


wishlist_bp = Blueprint('wishlist', __name__)


@wishlist_bp.route('/wishlist/additem', methods=['POST'])
@token_required(roles=['customer'])
def add_item_to_wishlist():
    data = request.get_json()
    
    # Validate request data
    required_fields = ['product_id']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    product_id = data.get('product_id')
    model_id = data.get('model_id')
    color_id = data.get('color_id')
    
    # Fetch the product to check if it exists
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    # Check if color exists if provided
    if color_id:
        product_color = ProductColor.query.get(color_id)
        if not product_color:
            return jsonify({'error': 'Product color not found'}), 404
    
    # Check if the user already has a wishlist, if not create one
    wishlist = Wishlist.query.filter_by(customer_id=request.current_user.customer_id).first()
    if not wishlist:
        wishlist = Wishlist(customer_id=request.current_user.customer_id)
        db.session.add(wishlist)
        db.session.flush()  # Flush to get the wishlist_id without committing
    
    # Check if the item already exists in the wishlist
    existing_item = WishlistItem.query.filter_by(
        wishlist_id=wishlist.wishlist_id,
        product_id=product_id,
        model_id=model_id,
        color_id=color_id,
        # spec_id=spec_id
    ).first()
    
    if existing_item:
        # Item already exists in wishlist, no need to add again
        return jsonify({
            'success': True,
            'message': 'Item already in wishlist',
            'wishlist_id': wishlist.wishlist_id
        }), 200
    else:
        # Create new wishlist item
        wishlist_item = WishlistItem(
            wishlist_id=wishlist.wishlist_id,
            product_id=product_id,
            model_id=model_id,
            color_id=color_id,
            # spec_id=spec_id
        )
        db.session.add(wishlist_item)
    
    # Commit all changes
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Item added to wishlist successfully',
        'wishlist_id': wishlist.wishlist_id
    }), 200


@wishlist_bp.route('/wishlist/deleteitem', methods=['DELETE'])
@token_required(roles=['customer'])
def delete_item_from_wishlist():
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
    
    # Check if the user has a wishlist
    wishlist = Wishlist.query.filter_by(customer_id=request.current_user.customer_id).first()
    if not wishlist:
        return jsonify({'error': 'No wishlist found for this user'}), 404
    
    # Find the wishlist item using product details
    query = WishlistItem.query.filter_by(
        wishlist_id=wishlist.wishlist_id,
        product_id=product_id
    )
    
    # Add optional filters if they were provided
    if model_id is not None:
        query = query.filter_by(model_id=model_id)
    if color_id is not None:
        query = query.filter_by(color_id=color_id)
    # if spec_id is not None:
    #     query = query.filter_by(spec_id=spec_id)
    
    wishlist_item = query.first()
    
    if not wishlist_item:
        return jsonify({'error': 'Item not found in wishlist'}), 404
    
    # Remove the wishlist item
    db.session.delete(wishlist_item)
    
    # Commit all changes
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Item removed from wishlist successfully',
        'wishlist_id': wishlist.wishlist_id
    }), 200


@wishlist_bp.route('/wishlist/getbycustid', methods=['GET'])
@token_required(roles=['customer'])
def get_wishlist_by_customer_id():
    customer_id = request.current_user.customer_id
    wishlist = Wishlist.query.filter_by(customer_id=customer_id).first()
    
    if not wishlist:
        return jsonify({
            'success': True,
            'wishlist': {
                'wishlist_id': None,
                'customer_id': customer_id,
                'items': [],
                'item_count': 0
            }
        }), 200
    
    # Get all items in the wishlist with detailed information
    wishlist_items = WishlistItem.query.filter_by(wishlist_id=wishlist.wishlist_id).all()
    
    items_list = []
    for item in wishlist_items:
        # Get product details
        product = Product.query.options(
            db.joinedload(Product.colors),
            db.joinedload(Product.models).joinedload(ProductModel.colors)
        ).get(item.product_id)
        
        # Get model details if applicable
        model = None
        if item.model_id:
            model = ProductModel.query.options(
                db.joinedload(ProductModel.colors)
            ).get(item.model_id)
        
        # Get color details if applicable
        color = None
        if item.color_id:
            color = ProductColor.query.get(item.color_id)
        
        # Get price using the same logic as products route
        if color:
            # Use selected color's price if available
            price = float(color.price)
            original_price = float(color.original_price) if color.original_price else None
            price_source = 'selected_color'
        elif product.product_type == 'single' and product.colors:
            # Fallback to first color price for single products
            price = float(product.colors[0].price)
            original_price = float(product.colors[0].original_price) if product.colors[0].original_price else None
            price_source = 'first_product_color'
        elif product.product_type == 'variable' and product.models and product.models[0].colors:
            # Fallback to first model's first color price for variable products
            price = float(product.models[0].colors[0].price)
            original_price = float(product.models[0].colors[0].original_price) if product.models[0].colors[0].original_price else None
            price_source = 'first_model_color'
        else:
            price = None
            original_price = None
            price_source = 'none'
        
        # Get product image (first one if available)
        product_image = None
        if product and product.images:
            product_image = product.images[0].image_url if product.images else None
        
        # Get color-specific image if available
        color_image = None
        if color and color.images:
            color_image = color.images[0].image_url if color.images else None
        
        # Get model image if available
        model_image = None
        if model and model.colors and model.colors[0].images:
            model_image = model.colors[0].images[0].image_url if model.colors[0].images else None
        
        # Construct detailed item information
        item_details = {
            'item_id': item.item_id,
            'product': {
                'product_id': product.product_id if product else None,
                'name': product.name if product else 'Unknown',
                'description': product.description if product else None,
                'product_type': product.product_type if product else None,
                'rating': float(product.rating) if product and product.rating else 0,
                'image_url': color_image or model_image or product_image,
                'price': price,
                'original_price': original_price,
                'price_source': price_source,
                'colors': [{
                    'color_id': c.color_id,
                    'name': c.name,
                    'price': float(c.price),
                    'original_price': float(c.original_price) if c.original_price else None
                } for c in product.colors] if product and product.colors else None,
                'models': [{
                    'model_id': m.model_id,
                    'name': m.name,
                    'colors': [{
                        'color_id': c.color_id,
                        'name': c.name,
                        'price': float(c.price),
                        'original_price': float(c.original_price) if c.original_price else None
                    } for c in m.colors]
                } for m in product.models] if product and product.models else None
            },
            'model': {
                'model_id': model.model_id if model else None,
                'name': model.name if model else None,
                'description': model.description if model else None
            } if model else None,
            'color': {
                'color_id': color.color_id if color else None,
                'name': color.name if color else None,
                'stock_quantity': color.stock_quantity if color else None
            } if color else None,
            'added_at': item.added_at.isoformat() if item.added_at else None
        }
        
        items_list.append(item_details)
    
    response = {
        'success': True,
        'wishlist': {
            'wishlist_id': wishlist.wishlist_id,
            'customer_id': customer_id,
            'created_at': wishlist.created_at.isoformat() if wishlist.created_at else None,
            'updated_at': wishlist.updated_at.isoformat() if wishlist.updated_at else None,
            'item_count': len(items_list),
            'items': items_list
        }
    }
    
    return jsonify(response), 200


@wishlist_bp.route('/wishlist/clear', methods=['DELETE'])
@token_required(roles=['customer'])
def clear_wishlist():
    customer_id = request.current_user.customer_id
    
    # Check if the user has a wishlist
    wishlist = Wishlist.query.filter_by(customer_id=customer_id).first()
    if not wishlist:
        return jsonify({
            'success': True,
            'message': 'No wishlist found for this user'
        }), 200
    
    # Delete all items from the wishlist
    WishlistItem.query.filter_by(wishlist_id=wishlist.wishlist_id).delete()
    
    # Commit the changes
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Wishlist cleared successfully',
        'wishlist_id': wishlist.wishlist_id

    }), 200

