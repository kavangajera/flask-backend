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
                product_dict['unit'] = product.unit
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
            product_dict['unit'] = product.unit
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
            new_product.unit = int(request.form.get('unit', 1))
            
            # Create default model for single product
            default_model = ProductModel(
                product_id=new_product.product_id,
                name="Default",
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
                
                if color_name and color_price:
                    # Create color linked to both product and default model
                    color = ProductColor(
                        product_id=new_product.product_id,
                        model_id=default_model.model_id,
                        name=color_name,
                        stock_quantity=int(color_stock),
                        price=float(color_price),
                        original_price=float(color_original_price) if color_original_price else None
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
                        
                        if color_name and color_price:
                            # Create color
                            color = ProductColor(
                                product_id=new_product.product_id,
                                model_id=model.model_id,
                                name=color_name,
                                stock_quantity=int(color_stock),
                                price=float(color_price),
                                original_price=float(color_original_price) if color_original_price else None
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