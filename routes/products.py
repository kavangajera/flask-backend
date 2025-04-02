import os
from venv import logger
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from extensions import db
from models.product import Product, ProductImage
from uuid import uuid4
from middlewares.auth import token_required

products_bp = Blueprint('products', __name__)


# List all products with their images and categories
@products_bp.route('/products', methods=['GET'])
def list_products(): 
    try:
        products = Product.query.options(db.joinedload(Product.images)).all()
        products_list = []
        for product in products:
            product_dict = {
                'product_id': product.product_id,
                'unit': product.unit,
                'rating': product.rating,
                'raters': product.raters,
                'description': product.description,
                'name': product.name,
                'category': product.category,
                'price': float(product.price) if product.price else None,
                'deleted_price': float(product.deleted_price) if product.deleted_price else None,
                'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in product.images]
            }
            products_list.append(product_dict)

        return jsonify(products_list)
    
    except Exception as e:
        
        return jsonify({'error': str(e)}), 500

# Get product details by product_id
@products_bp.route('/product/<int:product_id>', methods=['GET'])
def product_detail(product_id):
    try:
        product = Product.query.options(db.joinedload(Product.images)).get_or_404(product_id)

        product_dict = {
            'product_id': product.product_id,
            'unit': product.unit,
            'rating': product.rating,
            'raters': product.raters,
            'description': product.description,
            'name': product.name,
            'category': product.category,
            'price': float(product.price) if product.price else None,
            'deleted_price': float(product.deleted_price) if product.deleted_price else None,
            'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in product.images]
        }
        return jsonify(product_dict)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

UPLOAD_FOLDER = '/var/www/flask-backend/static/product_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@products_bp.route('/product/add', methods=['POST'])
@token_required(roles=['admin'])
def add_product():
    # At this point, the middleware has already:
    # 1. Verified the JWT token
    # 2. Checked that the user is an admin
    # We can access the current user via request.current_user
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Get product details from form data
    name = request.form.get('name')
    description = request.form.get('description')
    category = request.form.get('category')
    price = request.form.get('price')
    deleted_price = request.form.get('deleted_price', None)
    unit = request.form.get('unit', 1)

    # Validate required fields
    if not all([name, description, category, price]):
        return jsonify({'message': 'Missing required product details'}), 400

    # Create new product
    new_product = Product(
        name=name,
        description=description,
        category=category,
        price=float(price),
        deleted_price=float(deleted_price) if deleted_price else None,
        unit=int(unit),
        rating=0,
        raters=0
    )

    # Handle image uploads
    uploaded_images = request.files.getlist('images')
    product_images = []

    for image in uploaded_images:
        if image and allowed_file(image.filename):
            # Generate unique filename
            filename = f"{uuid4().hex}_{secure_filename(image.filename)}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # Save file
            image.save(file_path)
            
            # Create ProductImage instance
            product_image = ProductImage(
                image_url=f'/product_images/{filename}'
            )
            product_images.append(product_image)

    # Associate images with product
    new_product.images = product_images

    try:
        # Add to database
        db.session.add(new_product)
        db.session.add_all(product_images)
        db.session.commit()

        # Log the product addition
        logger.info(f"Product added by admin: {request.current_user.email} - Product ID: {new_product.product_id}")

        return jsonify({
            'message': 'Product added successfully!',
            'product_id': new_product.product_id
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding product by {request.current_user.email}: {str(e)}")
        return jsonify({'message': 'An error occurred while adding the product'}), 500
