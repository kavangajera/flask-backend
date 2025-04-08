import os
from venv import logger
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from extensions import db
from models.product import Product, ProductImage, ProductModel, ProductColor, ModelSpecification
from models.category import Category, Subcategory
from uuid import uuid4
from middlewares.auth import token_required

products_bp = Blueprint('products', __name__)

# List all products with their images and categories
@products_bp.route('/products', methods=['GET'])
def list_products(): 
    try:
        products = Product.query.options(
            db.joinedload(Product.images),
            db.joinedload(Product.main_category),
            db.joinedload(Product.sub_category)
        ).all() 
        
        products_list = []
        for product in products:
            product_dict = {
                'product_id': product.product_id,
                'name': product.name,
                'description': product.description,
                'category': product.main_category.name if product.main_category else None,
                'subcategory': product.sub_category.name if product.sub_category else None,
                'product_type': product.product_type,
                'rating': product.rating,
                'raters': product.raters,
                'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in product.images],
            }
            
            # Add models for all product types
            product_dict['models'] = []
            
            for model in product.models:
                model_dict = {
                    'model_id': model.model_id,
                    'name': model.name,
                    'description': model.description,
                    'colors': [],
                    'specifications': [
                        {'key': spec.key, 'value': spec.value} for spec in model.specifications
                    ]
                }
                
                for color in model.colors:
                    color_dict = {
                        'color_id': color.color_id,
                        'name': color.name,
                        'stock_quantity': color.stock_quantity,
                        'price': float(color.price),
                        'original_price': float(color.original_price) if color.original_price else None,
                        'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in color.images]
                    }
                    model_dict['colors'].append(color_dict)
                
                product_dict['models'].append(model_dict)
            
            # Add single product specific info
            if product.product_type == 'single':
            
                product_dict['colors'] = []
                
                for color in product.colors:
                    color_dict = {
                        'color_id': color.color_id,
                        'name': color.name,
                        'stock_quantity': color.stock_quantity,
                        'price': float(color.price),
                        'original_price': float(color.original_price) if color.original_price else None,
                        'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in color.images]
                    }
                    product_dict['colors'].append(color_dict)
            
            products_list.append(product_dict)

        return jsonify(products_list)

    except Exception as e:
        logger.error(f"Error listing products: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Get product details by product_id
@products_bp.route('/product/<int:product_id>', methods=['GET'])
def product_detail(product_id):
    try:
        product = Product.query.options(
            db.joinedload(Product.images),
            db.joinedload(Product.main_category),
            db.joinedload(Product.sub_category),
            db.joinedload(Product.models).joinedload(ProductModel.colors).joinedload(ProductColor.images),
            db.joinedload(Product.models).joinedload(ProductModel.specifications),
            db.joinedload(Product.colors).joinedload(ProductColor.images)
        ).get_or_404(product_id)

        product_dict = {
            'product_id': product.product_id,
            'name': product.name,
            'description': product.description,
            'category': product.main_category.name if product.main_category else None,
            'subcategory': product.sub_category.name if product.sub_category else None,
            'product_type': product.product_type,
            'rating': product.rating,
            'raters': product.raters,
            'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in product.images],
        }
        
        # Add models for all product types
        product_dict['models'] = []
        
        for model in product.models:
            model_dict = {
                'model_id': model.model_id,
                'name': model.name,
                'description': model.description,
                'colors': [],
                'specifications': [
                    {'key': spec.key, 'value': spec.value} for spec in model.specifications
                ]
            }
            
            for color in model.colors:
                color_dict = {
                    'color_id': color.color_id,
                    'name': color.name,
                    'stock_quantity': color.stock_quantity,
                    'price': float(color.price),
                    'original_price': float(color.original_price) if color.original_price else None,
                    'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in color.images]
                }
                model_dict['colors'].append(color_dict)
            
            product_dict['models'].append(model_dict)
        
        # Add single product specific info
        if product.product_type == 'single':
         
            product_dict['colors'] = []
            
            for color in product.colors:
                color_dict = {
                    'color_id': color.color_id,
                    'name': color.name,
                    'stock_quantity': color.stock_quantity,
                    'price': float(color.price),
                    'original_price': float(color.original_price) if color.original_price else None,
                    'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in color.images]
                }
                product_dict['colors'].append(color_dict)
        
        return jsonify(product_dict)
    
    except Exception as e:
        logger.error(f"Error getting product details: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Routes for categories
@products_bp.route('/categories', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.all()
        result = []
        
        for category in categories:
            cat_dict = {
                'category_id': category.category_id,
                'name': category.name,
                'image_url':category.image_url,
                'subcategories': []
            }
            
            for subcategory in category.subcategories:
                cat_dict['subcategories'].append({
                    'subcategory_id': subcategory.subcategory_id,
                    'name': subcategory.name
                })
            
            result.append(cat_dict)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return jsonify({'error': str(e)}), 500

UPLOAD_FOLDER = '/var/www/flask-backend/static/product_images'
ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp',
    'svg', 'ico', 'heif', 'heic', 'raw', 'psd', 'ai', 'eps', 'jfif',
    'avif'
}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(image_file):
    if image_file and allowed_file(image_file.filename):
        # Generate unique filename
        filename = f"{uuid4().hex}_{secure_filename(image_file.filename)}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save file
        image_file.save(file_path)
        return f'/product_images/{filename}'
    return None

@products_bp.route('/product/add', methods=['POST'])
@token_required(roles=['admin'])
def add_product():
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    try:
        # Extract basic product information
        name = request.form.get('name')
        description = request.form.get('description')
        product_type = request.form.get('product_type')
        
        # Handle category and subcategory
        category_id = request.form.get('category_id')
        subcategory_id = request.form.get('subcategory_id')
        
        # Check if we need to create a new category
        if not category_id and request.form.get('new_category'):
            new_category = Category(name=request.form.get('new_category'),image_url=save_image(request.files.get('image')))
            db.session.add(new_category)
            db.session.commit()  # Get the ID without committing
            category_id = new_category.category_id
        
        # Check if we need to create a new subcategory
        if category_id and not subcategory_id and request.form.get('new_subcategory'):
            new_subcategory = Subcategory(
                name=request.form.get('new_subcategory'),
                category_id=category_id
            )
            db.session.add(new_subcategory)
            db.session.commit()  # Get the ID without committing
            subcategory_id = new_subcategory.subcategory_id
        
        # Validate required fields
        print(name, description, category_id, product_type)
        if not all([name, description, category_id, product_type]):
            return jsonify({'message': 'Missing required product details'}), 400
        
        # Create new product
        new_product = Product(
            name=name,
            description=description,
            category_id=category_id,
            subcategory_id=subcategory_id,
            product_type=product_type,
            rating=0,
            raters=0
        )
        
        # Add product to session
        db.session.add(new_product)
        db.session.commit()  # Get the product ID
        
        # Handle product-level images
        product_images = request.files.getlist('product_images')
        for image_file in product_images:
            image_url = save_image(image_file)
            if image_url:
                product_image = ProductImage(
                    product_id=new_product.product_id,
                    image_url=image_url
                )
                db.session.add(product_image)
        
        # Handle Single Product
        if product_type == 'single':
            
            
            # Create default model for single product
            default_model = ProductModel(
                product_id=new_product.product_id,
                name=name,
                description=description
            )
            db.session.add(default_model)
            db.session.commit()  # Get the model ID
            
            # Process specifications using ModelSpecification
            specs_count = int(request.form.get('specs_count', 0))
            for i in range(specs_count):
                spec_key = request.form.get(f'spec_key_{i}')
                spec_value = request.form.get(f'spec_value_{i}')
                if spec_key and spec_value:
                    spec = ModelSpecification(
                        model_id=default_model.model_id,
                        key=spec_key,
                        value=spec_value
                    )
                    db.session.add(spec)
            
            # Process colors
            colors_count = int(request.form.get('colors_count', 0))
            for i in range(colors_count):
                color_name = request.form.get(f'color_name_{i}')
                color_price = request.form.get(f'color_price_{i}')
                color_original_price = request.form.get(f'color_original_price_{i}')
                color_stock = request.form.get(f'color_stock_{i}', 0)
                threshold = request.form.get(f'threshold_{i}', 10)
                
                if color_name and color_price:
                    # Create color linked to both product and default model
                    color = ProductColor(
                        product_id=new_product.product_id,
                        model_id=default_model.model_id,
                        name=color_name,
                        stock_quantity=int(color_stock),
                        price=float(color_price),
                        original_price=float(color_original_price) if color_original_price else None
                        ,threshold=int(threshold)
                        
                    )
                    db.session.add(color)
                    db.session.commit()  # Get color ID
                    
                    # Process color images
                    color_images = request.files.getlist(f'color_images_{i}')
                    for image_file in color_images:
                        image_url = save_image(image_file)
                        if image_url:
                            image = ProductImage(
                                product_id=new_product.product_id,
                                color_id=color.color_id,
                                image_url=image_url
                            )
                            db.session.add(image)
        
        # Handle Variable Product
        elif product_type == 'variable':
            # Process models
            models_count = int(request.form.get('models_count', 0))
            for i in range(models_count):
                model_name = request.form.get(f'model_name_{i}')
                model_description = request.form.get(f'model_description_{i}')
                
                if model_name and model_description:
                    # Create model
                    model = ProductModel(
                        product_id=new_product.product_id,
                        name=model_name,
                        description=model_description
                    )
                    db.session.add(model)
                    db.session.commit()  # Get model ID
                    
                    # Process model specifications
                    model_specs_count = int(request.form.get(f'model_specs_count_{i}', 0))
                    for j in range(model_specs_count):
                        spec_key = request.form.get(f'model_{i}_spec_key_{j}')
                        spec_value = request.form.get(f'model_{i}_spec_value_{j}')
                        if spec_key and spec_value:
                            spec = ModelSpecification(
                                model_id=model.model_id,
                                key=spec_key,
                                value=spec_value
                            )
                            db.session.add(spec)
                    
                    # Process model colors
                    model_colors_count = int(request.form.get(f'model_colors_count_{i}', 0))
                    for j in range(model_colors_count):
                        color_name = request.form.get(f'model_{i}_color_name_{j}')
                        color_price = request.form.get(f'model_{i}_color_price_{j}')
                        color_original_price = request.form.get(f'model_{i}_color_original_price_{j}')
                        color_stock = request.form.get(f'model_{i}_color_stock_{j}', 0)
                        threshold = request.form.get(f'model_{i}_threshold_{j}', 10)
                        if color_name and color_price:
                            # Create color
                            color = ProductColor(
                                product_id=new_product.product_id,
                                model_id=model.model_id,
                                name=color_name,
                                stock_quantity=int(color_stock),
                                price=float(color_price),
                                original_price=float(color_original_price) if color_original_price else None,
                                threshold=int(threshold)
                            )
                            db.session.add(color)
                            db.session.commit()  # Get color ID
                            
                            # Process color images
                            color_images = request.files.getlist(f'model_{i}_color_images_{j}')
                            for image_file in color_images:
                                image_url = save_image(image_file)
                                if image_url:
                                    image = ProductImage(
                                        product_id=new_product.product_id,
                                        color_id=color.color_id,
                                        image_url=image_url
                                    )
                                    db.session.add(image)
        
        # Commit all changes
        db.session.commit()
        
        logger.info(f"Product added by admin: {request.current_user.email} - Product ID: {new_product.product_id}")
        
        return jsonify({
            'message': 'Product added successfully!',
            'product_id': new_product.product_id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding product by {request.current_user.email}: {str(e)}")
        return jsonify({'message': f'An error occurred while adding the product: {str(e)}'}), 500



@products_bp.route('/category/add', methods=['POST'])
@token_required(roles=['admin'])
def add_category():
    try:
        name = request.form.get('name')
        image = request.files.get('image')

        if not name:
            return jsonify({'message': 'Category name is required'}), 400

        image_url = save_image(image)
        

        new_category = Category(name=name, image_url=image_url)
        db.session.add(new_category)
        db.session.commit()

        return jsonify({
            'message': 'Category added successfully!',
            'category_id': new_category.category_id,
            'name': new_category.name,
            'image_url': image_url
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding category: {str(e)}")
        return jsonify({'message': 'An error occurred while adding the category'}), 500


# Add subcategory endpoint
@products_bp.route('/subcategory/add', methods=['POST'])
@token_required(roles=['admin'])
def add_subcategory():
    try:
        name = request.json.get('name')
        category_id = request.json.get('category_id')
        
        if not name or not category_id:
            return jsonify({'message': 'Subcategory name and category_id are required'}), 400
        
        category = Category.query.get(category_id)
        if not category:
            return jsonify({'message': 'Category not found'}), 404
        
        new_subcategory = Subcategory(name=name, category_id=category_id)
        db.session.add(new_subcategory)
        db.session.commit()
        
        return jsonify({
            'message': 'Subcategory added successfully!',
            'subcategory_id': new_subcategory.subcategory_id,
            'name': new_subcategory.name,
            'category_id': new_subcategory.category_id
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding subcategory: {str(e)}")
        return jsonify({'message': 'An error occurred while adding the subcategory'}), 500
    

@products_bp.route('/products/by-category/<int:category_id>', methods=['GET'])
def get_products_by_category(category_id):
    try:
        products = Product.query.options(
            db.joinedload(Product.images),
            db.joinedload(Product.main_category),
            db.joinedload(Product.sub_category)
        ).filter(Product.category_id == category_id).all()
        
        if not products:
            return jsonify([])
        
        products_list = []
        for product in products:
            product_dict = {
                'product_id': product.product_id,
                'name': product.name,
                'description': product.description,
                'category': product.main_category.name if product.main_category else None,
                'subcategory': product.sub_category.name if product.sub_category else None,
                'product_type': product.product_type,
                'rating': product.rating,
                'raters': product.raters,
                'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in product.images],
            }
            
            # Add models for all product types
            product_dict['models'] = []
            
            for model in product.models:
                model_dict = {
                    'model_id': model.model_id,
                    'name': model.name,
                    'description': model.description,
                    'colors': [],
                    'specifications': [
                        {'key': spec.key, 'value': spec.value} for spec in model.specifications
                    ]
                }
                
                for color in model.colors:
                    color_dict = {
                        'color_id': color.color_id,
                        'name': color.name,
                        'stock_quantity': color.stock_quantity,
                        'price': float(color.price),
                        'original_price': float(color.original_price) if color.original_price else None,
                        'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in color.images]
                    }
                    model_dict['colors'].append(color_dict)
                
                product_dict['models'].append(model_dict)
            
            # Add single product specific info
            if product.product_type == 'single':
               
                product_dict['colors'] = []
                
                for color in product.colors:
                    color_dict = {
                        'color_id': color.color_id,
                        'name': color.name,
                        'stock_quantity': color.stock_quantity,
                        'price': float(color.price),
                        'original_price': float(color.original_price) if color.original_price else None,
                        'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in color.images]
                    }
                    product_dict['colors'].append(color_dict)
            
            products_list.append(product_dict)

        return jsonify(products_list)

    except Exception as e:
        logger.error(f"Error getting products by category: {str(e)}")
        return jsonify({'error': str(e)}), 500


from datetime import datetime




# Constants for image uploads
UPLOAD_FOLDER = '/var/www/flask-backend/static/product_images'
ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp',
    'svg', 'ico', 'heif', 'heic', 'raw', 'psd', 'ai', 'eps', 'jfif',
    'avif'
}

# Helper functions for image uploads
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(image_file):
    if image_file and allowed_file(image_file.filename):
        # Generate unique filename
        filename = f"{uuid4().hex}_{secure_filename(image_file.filename)}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save file
        image_file.save(file_path)
        return f'/product_images/{filename}'
    return None

# Update an entire product (PUT)
@products_bp.route('/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.form.to_dict() if request.form else request.json
    
    # Update basic product information
    product.name = data.get('name', product.name)
    product.description = data.get('description', product.description)
    product.category_id = data.get('category_id', product.category_id)
    product.subcategory_id = data.get('subcategory_id', product.subcategory_id)
    product.product_type = data.get('product_type', product.product_type)
    product.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({'message': 'Product updated successfully', 'product_id': product.product_id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Partially update a product (PATCH)
@products_bp.route('/<int:product_id>', methods=['PATCH'])
def partially_update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.form.to_dict() if request.form else request.json
    
    # Update only the fields that are provided
    if 'name' in data:
        product.name = data['name']
    if 'description' in data:
        product.description = data['description']
    if 'category_id' in data:
        product.category_id = data['category_id']
    if 'subcategory_id' in data:
        product.subcategory_id = data['subcategory_id']
    if 'product_type' in data:
        product.product_type = data['product_type']
  
    
    product.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({'message': 'Product partially updated', 'product_id': product.product_id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Delete a product
@products_bp.route('/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Get all image paths to delete files from filesystem
    image_paths = []
    for image in product.images:
        if image.image_url and not image.image_url.startswith('http'):
            image_paths.append(image.image_url.replace('/product_images/', ''))
    
    try:
        # Delete product from database (cascade will handle related records)
        db.session.delete(product)
        db.session.commit()
        
        # Delete image files from filesystem
        for img_path in image_paths:
            try:
                file_path = os.path.join(UPLOAD_FOLDER, img_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                # Log error but continue with other operations
                print(f"Error deleting file {img_path}: {str(e)}")
        
        return jsonify({'message': 'Product deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ----- Product Images Routes -----

# Add new product image
@products_bp.route('/<int:product_id>/images', methods=['POST'])
def add_product_image(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Check if image file is provided
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    image_file = request.files['image']
    image_url = save_image(image_file)
    
    if not image_url:
        return jsonify({'error': 'Invalid image file'}), 400
    
    # Get color_id from form data if available
    color_id = None
    if request.form and 'color_id' in request.form:
        color_id = request.form.get('color_id')
    
    new_image = ProductImage(
        product_id=product_id,
        color_id=color_id,
        image_url=image_url
    )
    
    try:
        db.session.add(new_image)
        db.session.commit()
        return jsonify({
            'message': 'Image added successfully',
            'image_id': new_image.image_id,
            'image_url': image_url
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Update product image
@products_bp.route('/<int:product_id>/images/<int:image_id>', methods=['PUT'])
def update_product_image(product_id, image_id):
    image = ProductImage.query.get_or_404(image_id)
    if image.product_id != product_id:
        return jsonify({'error': 'Image does not belong to this product'}), 400
    
    old_image_path = None
    if image.image_url and not image.image_url.startswith('http'):
        old_image_path = image.image_url.replace('/product_images/', '')
    
    # Check if a new image file is provided
    if 'image' in request.files:
        image_file = request.files['image']
        image_url = save_image(image_file)
        
        if image_url:
            image.image_url = image_url
    
    # Update color_id if provided
    if request.form and 'color_id' in request.form:
        image.color_id = request.form.get('color_id')
    
    try:
        db.session.commit()
        
        # Delete old image file if replaced
        if old_image_path and image.image_url != f'/product_images/{old_image_path}':
            try:
                file_path = os.path.join(UPLOAD_FOLDER, old_image_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                # Log error but continue with other operations
                print(f"Error deleting file {old_image_path}: {str(e)}")
        
        return jsonify({
            'message': 'Image updated successfully',
            'image_url': image.image_url
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Delete product image
@products_bp.route('/<int:product_id>/images/<int:image_id>', methods=['DELETE'])
def delete_product_image(product_id, image_id):
    image = ProductImage.query.get_or_404(image_id)
    if image.product_id != product_id:
        return jsonify({'error': 'Image does not belong to this product'}), 400
    
    # Store image path to delete file after database record
    image_path = None
    if image.image_url and not image.image_url.startswith('http'):
        image_path = image.image_url.replace('/product_images/', '')
    
    try:
        db.session.delete(image)
        db.session.commit()
        
        # Delete image file from filesystem
        if image_path:
            try:
                file_path = os.path.join(UPLOAD_FOLDER, image_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                # Log error but continue with other operations
                print(f"Error deleting file {image_path}: {str(e)}")
        
        return jsonify({'message': 'Image deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ----- Product Models Routes -----

# Add new product model
@products_bp.route('/<int:product_id>/models', methods=['POST'])
def add_product_model(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.form.to_dict() if request.form else request.json
    
    new_model = ProductModel(
        product_id=product_id,
        name=data['name'],
        description=data['description']
    )
    
    try:
        db.session.add(new_model)
        db.session.commit()
        return jsonify({'message': 'Model added successfully', 'model_id': new_model.model_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Update product model
@products_bp.route('/<int:product_id>/models/<int:model_id>', methods=['PUT'])
def update_product_model(product_id, model_id):
    model = ProductModel.query.get_or_404(model_id)
    if model.product_id != product_id:
        return jsonify({'error': 'Model does not belong to this product'}), 400
        
    data = request.form.to_dict() if request.form else request.json
    
    model.name = data.get('name', model.name)
    model.description = data.get('description', model.description)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Model updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Delete product model
@products_bp.route('/<int:product_id>/models/<int:model_id>', methods=['DELETE'])
def delete_product_model(product_id, model_id):
    model = ProductModel.query.get_or_404(model_id)
    if model.product_id != product_id:
        return jsonify({'error': 'Model does not belong to this product'}), 400
    
    try:
        db.session.delete(model)
        db.session.commit()
        return jsonify({'message': 'Model deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ----- Product Colors Routes -----

# Add new product color
@products_bp.route('/<int:product_id>/colors', methods=['POST'])
def add_product_color(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.form.to_dict() if request.form else request.json
    
    new_color = ProductColor(
        product_id=product_id,
        model_id=data.get('model_id'),
        name=data['name'],
        stock_quantity=data.get('stock_quantity', 0),
        price=data['price'],
        original_price=data.get('original_price'),
        threshold=data.get('threshold', 10)
    )
    
    try:
        db.session.add(new_color)
        db.session.commit()
        return jsonify({'message': 'Color added successfully', 'color_id': new_color.color_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Update product color
@products_bp.route('/<int:product_id>/colors/<int:color_id>', methods=['PUT'])
def update_product_color(product_id, color_id):
    color = ProductColor.query.get_or_404(color_id)
    if color.product_id != product_id:
        return jsonify({'error': 'Color does not belong to this product'}), 400
        
    data = request.form.to_dict() if request.form else request.json
    
    color.model_id = data.get('model_id', color.model_id)
    color.name = data.get('name', color.name)
    color.stock_quantity = data.get('stock_quantity', color.stock_quantity)
    color.price = data.get('price', color.price)
    color.original_price = data.get('original_price', color.original_price)
    color.threshold = data.get('threshold', color.threshold)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Color updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Partially update product color (specifically for stock update)
@products_bp.route('/<int:product_id>/colors/<int:color_id>', methods=['PATCH'])
def partially_update_product_color(product_id, color_id):
    color = ProductColor.query.get_or_404(color_id)
    if color.product_id != product_id:
        return jsonify({'error': 'Color does not belong to this product'}), 400
        
    data = request.form.to_dict() if request.form else request.json
    
    if 'stock_quantity' in data:
        color.stock_quantity = data['stock_quantity']
    if 'price' in data:
        color.price = data['price']
    if 'original_price' in data:
        color.original_price = data['original_price']
    if 'threshold' in data:
        color.threshold = data['threshold']
    if 'name' in data:
        color.name = data['name']
    if 'model_id' in data:
        color.model_id = data['model_id']
    
    try:
        db.session.commit()
        return jsonify({'message': 'Color partially updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Delete product color
@products_bp.route('/<int:product_id>/colors/<int:color_id>', methods=['DELETE'])
def delete_product_color(product_id, color_id):
    color = ProductColor.query.get_or_404(color_id)
    if color.product_id != product_id:
        return jsonify({'error': 'Color does not belong to this product'}), 400
    
    try:
        db.session.delete(color)
        db.session.commit()
        return jsonify({'message': 'Color deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ----- Product Specifications Routes -----

# Add new product specification
@products_bp.route('/<int:product_id>/specifications', methods=['POST'])
def add_product_specification(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.form.to_dict() if request.form else request.json
    
    new_spec = ModelSpecification(
        product_id=product_id,
        key=data['key'],
        value=data['value']
    )
    
    try:
        db.session.add(new_spec)
        db.session.commit()
        return jsonify({'message': 'Specification added successfully', 'spec_id': new_spec.spec_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Update product specification
@products_bp.route('/<int:product_id>/specifications/<int:spec_id>', methods=['PUT'])
def update_product_specification(product_id, spec_id):
    spec = ModelSpecification.query.get_or_404(spec_id)
    if spec.product_id != product_id:
        return jsonify({'error': 'Specification does not belong to this product'}), 400
        
    data = request.form.to_dict() if request.form else request.json
    
    spec.key = data.get('key', spec.key)
    spec.value = data.get('value', spec.value)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Specification updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Delete product specification
@products_bp.route('/<int:product_id>/specifications/<int:spec_id>', methods=['DELETE'])
def delete_product_specification(product_id, spec_id):
    spec = ModelSpecification.query.get_or_404(spec_id)
    if spec.product_id != product_id:
        return jsonify({'error': 'Specification does not belong to this product'}), 400
    
    try:
        db.session.delete(spec)
        db.session.commit()
        return jsonify({'message': 'Specification deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ----- Model Specifications Routes -----

# Add new model specification
@products_bp.route('/<int:product_id>/models/<int:model_id>/specifications', methods=['POST'])
def add_model_specification(product_id, model_id):
    model = ProductModel.query.get_or_404(model_id)
    if model.product_id != product_id:
        return jsonify({'error': 'Model does not belong to this product'}), 400
        
    data = request.form.to_dict() if request.form else request.json
    
    new_spec = ModelSpecification(
        model_id=model_id,
        key=data['key'],
        value=data['value']
    )
    
    try:
        db.session.add(new_spec)
        db.session.commit()
        return jsonify({'message': 'Model specification added successfully', 'spec_id': new_spec.spec_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Update model specification
@products_bp.route('/<int:product_id>/models/<int:model_id>/specifications/<int:spec_id>', methods=['PUT'])
def update_model_specification(product_id, model_id, spec_id):
    model = ProductModel.query.get_or_404(model_id)
    if model.product_id != product_id:
        return jsonify({'error': 'Model does not belong to this product'}), 400
        
    spec = ModelSpecification.query.get_or_404(spec_id)
    if spec.model_id != model_id:
        return jsonify({'error': 'Specification does not belong to this model'}), 400
        
    data = request.form.to_dict() if request.form else request.json
    
    spec.key = data.get('key', spec.key)
    spec.value = data.get('value', spec.value)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Model specification updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Delete model specification
@products_bp.route('/<int:product_id>/models/<int:model_id>/specifications/<int:spec_id>', methods=['DELETE'])
def delete_model_specification(product_id, model_id, spec_id):
    model = ProductModel.query.get_or_404(model_id)
    if model.product_id != product_id:
        return jsonify({'error': 'Model does not belong to this product'}), 400
        
    spec = ModelSpecification.query.get_or_404(spec_id)
    if spec.model_id != model_id:
        return jsonify({'error': 'Specification does not belong to this model'}), 400
    
    try:
        db.session.delete(spec)
        db.session.commit()
        return jsonify({'message': 'Model specification deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Batch update product rating
@products_bp.route('/<int:product_id>/rating', methods=['PATCH'])
def update_product_rating(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.form.to_dict() if request.form else request.json
    
    if 'rating' in data and 'raters' in data:
        product.rating = data['rating']
        product.raters = data['raters']
    elif 'rating' in data:
        # If adding a new rating
        new_rating = float(data['rating'])
        current_total = product.rating * product.raters
        product.raters += 1
        product.rating = (current_total + new_rating) / product.raters
    
    try:
        db.session.commit()
        return jsonify({'message': 'Product rating updated successfully', 'new_rating': product.rating}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400