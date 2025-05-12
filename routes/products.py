import os
from venv import logger
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from extensions import db
from models.cart import CartItem
from models.product import Product, ProductImage, ProductModel, ProductColor, ModelSpecification, ProductSpecification
from models.category import Category, Subcategory
from models.hsn import HSN
from uuid import uuid4
from middlewares.auth import token_required
import json
from sqlalchemy import func

from models.wishlist import WishlistItem
from urllib.parse import unquote

products_bp = Blueprint('products', __name__)

# List all products with their images and categories
@products_bp.route('/products', methods=['GET'])
def list_products(): 
    try:
        products = Product.query.options(
            db.joinedload(Product.images),
            db.joinedload(Product.main_category),
            db.joinedload(Product.sub_category),
            db.joinedload(Product.hsn),
        ).all() 
        
        products_list = []
        for product in products:
            product_dict = {
                'product_id': product.product_id,
                'name': product.name,
                'description': product.description,
                'category': product.main_category.name if product.main_category else None,
                'subcategory': product.sub_category.name if product.sub_category else None,
                'hsn': product.hsn.hsn_code if product.hsn else None,
                'sku_id': product.sku_id,
                'product_type': product.product_type,
                'rating': product.rating,
                'raters': product.raters,
                'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in product.images],
                'specifications': [{'spec_id': s.spec_id, 'key': s.key, 'value': s.value} for s in product.specifications],

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
                        {'spec_id': spec.spec_id , 'key': spec.key, 'value': spec.value} for spec in model.specifications
                    ]
                }
                
                for color in model.colors:
                    color_dict = {
                        'color_id': color.color_id,
                        'name': color.name,
                        'stock_quantity': color.stock_quantity,
                        'price': float(color.price),
                        'original_price': float(color.original_price) if color.original_price else None,
                        'threshold': color.threshold,
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
                        'threshold': color.threshold,
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
            db.joinedload(Product.hsn),
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
            'hsn_id': product.hsn.hsn_code if product.hsn else None,
            'sku_id': product.sku_id,
            'product_type': product.product_type,
            'rating': product.rating,
            'raters': product.raters,
            'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in product.images],
            'specifications': [{'spec_id': s.spec_id, 'key': s.key, 'value': s.value} for s in product.specifications],
        }
        
        # Add models for all product types
        product_dict['models'] = []
        
        for model in product.models:
            model_dict = {
                'model_id': model.model_id,
                'name': model.name,
                'description': model.description,
                'colors': [],
                'specifications': [{'spec_id': s.spec_id, 'key': s.key, 'value': s.value} for s in model.specifications],
            }
            
            for color in model.colors:
                color_dict = {
                    'color_id': color.color_id,
                    'name': color.name,
                    'stock_quantity': color.stock_quantity,
                    'price': float(color.price),
                    'original_price': float(color.original_price) if color.original_price else None,
                    'threshold': color.threshold,
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
                    'threshold': color.threshold,
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
    
# ROUTE FOR HSN 
@products_bp.route('/hsn', methods=['GET'])
def get_hsn():
    try:
        hsn_list = HSN.query.all()
        result = []
        
        for hsn in hsn_list:
            result.append({
                'hsn_id': hsn.hsn_id,
                'hsn_code': hsn.hsn_code if hsn else None,
                'description': hsn.hsn_description  # Corrected field name

            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting HSN: {str(e)}")
        return jsonify({'error': str(e)}), 500
    


UPLOAD_FOLDER = '/var/www/flask-backend/static/product_images'
ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp',
    'svg', 'ico', 'heif', 'heic', 'raw', 'psd', 'ai', 'eps', 'jfif',
    'avif' ,'mp4', 'mov', 'avi', 'mkv', 'webm', 'wmv', 'flv', 'm4v',
  'mpeg', 'mpg', '3gp', '3g2', 'ogv', 'mts', 'm2ts', 'ts',
  'mxf', 'f4v',  'apng', 'flc', 'fli', 'swf'
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

from flask import send_from_directory

@products_bp.route('/product_images/<path:filename>')
def serve_product_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# @products_bp.route('/product/add', methods=['POST'])
# @token_required(roles=['admin'])
# def add_product():
#     # Ensure upload directory exists
#     os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#     try:
#         # Extract basic product information
#         name = request.form.get('name')
#         description = request.form.get('description')
#         product_type = request.form.get('product_type')
        
#         # Handle category and subcategory
#         category_id = request.form.get('category_id')
#         subcategory_id = request.form.get('subcategory_id')
        
#         # Check if we need to create a new category
#         if not category_id and request.form.get('new_category'):
#             new_category = Category(name=request.form.get('new_category'),image_url=save_image(request.files.get('image')))
#             db.session.add(new_category)
#             db.session.commit()  # Get the ID without committing
#             category_id = new_category.category_id
        
#         # Check if we need to create a new subcategory
#         if category_id and not subcategory_id and request.form.get('new_subcategory'):
#             new_subcategory = Subcategory(
#                 name=request.form.get('new_subcategory'),
#                 category_id=category_id
#             )
#             db.session.add(new_subcategory)
#             db.session.commit()  # Get the ID without committing
#             subcategory_id = new_subcategory.subcategory_id
        
#         # Validate required fields
#         print(name, description, category_id, product_type)
#         if not all([name, description, category_id, product_type]):
#             return jsonify({'message': 'Missing required product details'}), 400
        
#         # Create new product
#         new_product = Product(
#             name=name,
#             description=description,
#             category_id=category_id,
#             subcategory_id=subcategory_id,
#             product_type=product_type,
#             rating=0,
#             raters=0
#         )
        
#         # Add product to session
#         db.session.add(new_product)
#         db.session.commit()  # Get the product ID
        
#         # Handle product-level images
#         product_images = request.files.getlist('product_images')
#         for image_file in product_images:
#             image_url = save_image(image_file)
#             if image_url:
#                 product_image = ProductImage(
#                     product_id=new_product.product_id,
#                     image_url=image_url
#                 )
#                 db.session.add(product_image)
        
#         # Handle Single Product
#         if product_type == 'single':
            
            
#             # Create default model for single product
#             default_model = ProductModel(
#                 product_id=new_product.product_id,
#                 name=name,
#                 description=description
#             )
#             db.session.add(default_model)
#             db.session.commit()  # Get the model ID
            
#             # Process specifications using ModelSpecification
#             specs_count = int(request.form.get('specs_count', 0))
#             for i in range(specs_count):
#                 spec_key = request.form.get(f'spec_key_{i}')
#                 spec_value = request.form.get(f'spec_value_{i}')
#                 if spec_key and spec_value:
#                     spec = ModelSpecification(
#                         model_id=default_model.model_id,
#                         key=spec_key,
#                         value=spec_value
#                     )
#                     db.session.add(spec)
            
#             # Process colors
#             colors_count = int(request.form.get('colors_count', 0))
#             for i in range(colors_count):
#                 color_name = request.form.get(f'color_name_{i}')
#                 color_price = request.form.get(f'color_price_{i}')
#                 color_original_price = request.form.get(f'color_original_price_{i}')
#                 color_stock = request.form.get(f'color_stock_{i}', 0)
#                 threshold = request.form.get(f'threshold_{i}', 10)
                
#                 if color_name and color_price:
#                     # Create color linked to both product and default model
#                     color = ProductColor(
#                         product_id=new_product.product_id,
#                         model_id=default_model.model_id,
#                         name=color_name,
#                         stock_quantity=int(color_stock),
#                         price=float(color_price),
#                         original_price=float(color_original_price) if color_original_price else None
#                         ,threshold=int(threshold)
                        
#                     )
#                     db.session.add(color)
#                     db.session.commit()  # Get color ID
                    
#                     # Process color images
#                     color_images = request.files.getlist(f'color_images_{i}')
#                     for image_file in color_images:
#                         image_url = save_image(image_file)
#                         if image_url:
#                             image = ProductImage(
#                                 product_id=new_product.product_id,
#                                 color_id=color.color_id,
#                                 image_url=image_url
#                             )
#                             db.session.add(image)
        
#         # Handle Variable Product
#         elif product_type == 'variable':
#             # Process models
#             models_count = int(request.form.get('models_count', 0))
#             for i in range(models_count):
#                 model_name = request.form.get(f'model_name_{i}')
#                 model_description = request.form.get(f'model_description_{i}')
                
#                 if model_name and model_description:
#                     # Create model
#                     model = ProductModel(
#                         product_id=new_product.product_id,
#                         name=model_name,
#                         description=model_description
#                     )
#                     db.session.add(model)
#                     db.session.commit()  # Get model ID
                    
#                     # Process model specifications
#                     model_specs_count = int(request.form.get(f'model_specs_count_{i}', 0))
#                     for j in range(model_specs_count):
#                         spec_key = request.form.get(f'model_{i}_spec_key_{j}')
#                         spec_value = request.form.get(f'model_{i}_spec_value_{j}')
#                         if spec_key and spec_value:
#                             spec = ModelSpecification(
#                                 model_id=model.model_id,
#                                 key=spec_key,
#                                 value=spec_value
#                             )
#                             db.session.add(spec)
                    
#                     # Process model colors
#                     model_colors_count = int(request.form.get(f'model_colors_count_{i}', 0))
#                     for j in range(model_colors_count):
#                         color_name = request.form.get(f'model_{i}_color_name_{j}')
#                         color_price = request.form.get(f'model_{i}_color_price_{j}')
#                         color_original_price = request.form.get(f'model_{i}_color_original_price_{j}')
#                         color_stock = request.form.get(f'model_{i}_color_stock_{j}', 0)
#                         threshold = request.form.get(f'model_{i}_threshold_{j}', 10)
#                         if color_name and color_price:
#                             # Create color
#                             color = ProductColor(
#                                 product_id=new_product.product_id,
#                                 model_id=model.model_id,
#                                 name=color_name,
#                                 stock_quantity=int(color_stock),
#                                 price=float(color_price),
#                                 original_price=float(color_original_price) if color_original_price else None,
#                                 threshold=int(threshold)
#                             )
#                             db.session.add(color)
#                             db.session.commit()  # Get color ID
                            
#                             # Process color images
#                             color_images = request.files.getlist(f'model_{i}_color_images_{j}')
#                             for image_file in color_images:
#                                 image_url = save_image(image_file)
#                                 if image_url:
#                                     image = ProductImage(
#                                         product_id=new_product.product_id,
#                                         color_id=color.color_id,
#                                         image_url=image_url
#                                     )
#                                     db.session.add(image)
        
#         # Commit all changes
#         db.session.commit()
        
#         logger.info(f"Product added by admin: {request.current_user.email} - Product ID: {new_product.product_id}")
        
#         return jsonify({
#             'message': 'Product added successfully!',
#             'product_id': new_product.product_id
#         }), 201
        
#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Error adding product by {request.current_user.email}: {str(e)}")
#         return jsonify({'message': f'An error occurred while adding the product: {str(e)}'}), 500





# @products_bp.route('/product/add', methods=['POST'])
# @token_required(roles=['admin'])
# def add_product():
#     # Ensure upload directory exists
#     os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#     try:
#         # Extract basic product information
#         name = request.form.get('name')
#         description = request.form.get('description')
#         product_type = request.form.get('product_type')
        
#         # Handle category and subcategory
#         category_id = request.form.get('category_id')
#         subcategory_id = request.form.get('subcategory_id')
#         hsn_id = request.form.get('hsn_id')
        
#         # Check if we need to create a new category
#         if not category_id and request.form.get('new_category'):
#             new_category = Category(name=request.form.get('new_category'),image_url=save_image(request.files.get('image')))
#             db.session.add(new_category)
#             db.session.commit()  # Get the ID without committing
#             category_id = new_category.category_id
        
#         # Check if we need to create a new subcategory
#         if category_id and not subcategory_id and request.form.get('new_subcategory'):
#             new_subcategory = Subcategory(
#                 name=request.form.get('new_subcategory'),
#                 category_id=category_id
#             )
#             db.session.add(new_subcategory)
#             db.session.commit()  # Get the ID without committing
#             subcategory_id = new_subcategory.subcategory_id
        
#         if not hsn_id and request.form.get('new_hsn'):
#             new_hsn = HSN(
#                 hsn_code=request.form.get('new_hsn_code'),
#             )
#             db.session.add(new_hsn)
#             db.session.commit()
#             hsn_id=new_hsn.hsn_id
        
#         # Validate required fields
#         print(name, description, category_id, product_type)
#         if not all([name, description, category_id, product_type]):
#             return jsonify({'message': 'Missing required product details'}), 400
        
#         # Create new product
#         new_product = Product(
#             name=name,
#             description=description,
#             category_id=category_id,
#             subcategory_id=subcategory_id,
#             hsn_id=hsn_id,
#             product_type=product_type,
#             rating=0,
#             raters=0
#         )
        
#         # Add product to session
#         db.session.add(new_product)
#         db.session.commit()  # Get the product ID
        
#         # Handle product-level images
#         product_images = request.files.getlist('product_images')
#         for image_file in product_images:
#             image_url = save_image(image_file)
#             if image_url:
#                 product_image = ProductImage(
#                     product_id=new_product.product_id,
#                     image_url=image_url
#                 )
#                 db.session.add(product_image)
        
#         # Handle Single Product
#         if product_type == 'single':
            
            
#             # Create default model for single product
#             default_model = ProductModel(
#                 product_id=new_product.product_id,
#                 name=name,
#                 description=description
#             )
#             db.session.add(default_model)
#             db.session.commit()  # Get the model ID
            
#             # Process specifications using ModelSpecification
#             specs_count = int(request.form.get('specs_count', 0))
#             for i in range(specs_count):
#              spec_key = request.form.get(f'spec_key_{i}')
#             spec_value = request.form.get(f'spec_value_{i}')
#             if spec_key and spec_value:
#                 spec = ProductSpecification(
#                 product_id=new_product.product_id,  # Direct product link
#                 key=spec_key,
#                 value=spec_value
#             )
#             db.session.add(spec)
            
#             # Process colors
#             colors_count = int(request.form.get('colors_count', 0))
#             for i in range(colors_count):
#                 color_name = request.form.get(f'color_name_{i}')
#                 color_price = request.form.get(f'color_price_{i}')
#                 color_original_price = request.form.get(f'color_original_price_{i}')
#                 color_stock = request.form.get(f'color_stock_{i}', 0)
#                 threshold = request.form.get(f'threshold_{i}', 10)
                
#                 if color_name and color_price:
#                     # Create color linked to both product and default model
#                     color = ProductColor(
#                         product_id=new_product.product_id,
#                         model_id=default_model.model_id,
#                         name=color_name,
#                         stock_quantity=int(color_stock),
#                         price=float(color_price),
#                         original_price=float(color_original_price) if color_original_price else None
#                         ,threshold=int(threshold)
                        
#                     )
#                     db.session.add(color)
#                     db.session.commit()  # Get color ID
                    
#                     # Process color images
#                     color_images = request.files.getlist(f'color_images_{i}')
#                     for image_file in color_images:
#                         image_url = save_image(image_file)
#                         if image_url:
#                             image = ProductImage(
#                                 product_id=new_product.product_id,
#                                 color_id=color.color_id,
#                                 image_url=image_url
#                             )
#                             db.session.add(image)
        
#         # Handle Variable Product
#         elif product_type == 'variable':
#             # Process models
#             models_count = int(request.form.get('models_count', 0))
#             for i in range(models_count):
#                 model_name = request.form.get(f'model_name_{i}')
#                 model_description = request.form.get(f'model_description_{i}')
                
#                 if model_name and model_description:
#                     # Create model
#                     model = ProductModel(
#                         product_id=new_product.product_id,
#                         name=model_name,
#                         description=model_description
#                     )
#                     db.session.add(model)
#                     db.session.commit()  # Get model ID
                    
#                     # Process model specifications
#                     model_specs_count = int(request.form.get(f'model_specs_count_{i}', 0))
#                     for j in range(model_specs_count):
#                         spec_key = request.form.get(f'model_{i}_spec_key_{j}')
#                         spec_value = request.form.get(f'model_{i}_spec_value_{j}')
#                         if spec_key and spec_value:
#                             spec = ModelSpecification(
#                                 model_id=model.model_id,
#                                 key=spec_key,
#                                 value=spec_value
#                             )
#                             db.session.add(spec)
                    
#                     # Process model colors
#                     model_colors_count = int(request.form.get(f'model_colors_count_{i}', 0))
#                     for j in range(model_colors_count):
#                         color_name = request.form.get(f'model_{i}_color_name_{j}')
#                         color_price = request.form.get(f'model_{i}_color_price_{j}')
#                         color_original_price = request.form.get(f'model_{i}_color_original_price_{j}')
#                         color_stock = request.form.get(f'model_{i}_color_stock_{j}', 0)
#                         threshold = request.form.get(f'model_{i}_threshold_{j}', 10)
#                         if color_name and color_price:
#                             # Create color
#                             color = ProductColor(
#                                 product_id=new_product.product_id,
#                                 model_id=model.model_id,
#                                 name=color_name,
#                                 stock_quantity=int(color_stock),
#                                 price=float(color_price),
#                                 original_price=float(color_original_price) if color_original_price else None,
#                                 threshold=int(threshold)
#                             )
#                             db.session.add(color)
#                             db.session.commit()  # Get color ID
                            
#                             # Process color images
#                             color_images = request.files.getlist(f'model_{i}_color_images_{j}')
#                             for image_file in color_images:
#                                 image_url = save_image(image_file)
#                                 if image_url:
#                                     image = ProductImage(
#                                         product_id=new_product.product_id,
#                                         color_id=color.color_id,
#                                         image_url=image_url
#                                     )
#                                     db.session.add(image)
        
#         # Commit all changes
#         db.session.commit()
        
#         logger.info(f"Product added by admin: {request.current_user.email} - Product ID: {new_product.product_id}")
        
#         return jsonify({
#             'message': 'Product added successfully!',
#             'product_id': new_product.product_id
#         }), 201
        
#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Error adding product by {request.current_user.email}: {str(e)}")
#         return jsonify({'message': f'An error occurred while adding the product: {str(e)}'}), 500



# Add a new product
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

        # Handle category, subcategory, and hsn
        category_id = request.form.get('category_id')
        subcategory_id = request.form.get('subcategory_id')
        hsn_id = request.form.get('hsn_id')

        # Check if we need to create a new category
        if not category_id and request.form.get('new_category'):
            new_category = Category(
                name=request.form.get('new_category'),
                image_url=save_image(request.files.get('image'))
            )
            db.session.add(new_category)
            db.session.commit()
            category_id = new_category.category_id

        # Check if we need to create a new subcategory
        if category_id and not subcategory_id and request.form.get('new_subcategory'):
            new_subcategory = Subcategory(
                name=request.form.get('new_subcategory'),
                category_id=category_id
            )
            db.session.add(new_subcategory)
            db.session.commit()
            subcategory_id = new_subcategory.subcategory_id

        # Check if we need to create a new HSN
        if not hsn_id and request.form.get('new_hsn_code'):
            new_hsn = HSN(
                hsn_code=request.form.get('new_hsn_code'),
                hsn_description=request.form.get('new_hsn_description', '')
            )
            db.session.add(new_hsn)
            db.session.commit()
            hsn_id = new_hsn.hsn_id

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
            hsn_id=hsn_id,
            product_type=product_type,
            rating=0,
            raters=0
        )
        db.session.add(new_product)
        db.session.commit()

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
            db.session.commit()

            # Process specifications
            specs_count = int(request.form.get('specs_count', 0))
            for i in range(specs_count):
                spec_key = request.form.get(f'spec_key_{i}')
                spec_value = request.form.get(f'spec_value_{i}')
                if spec_key and spec_value:
                    spec = ProductSpecification(
                        product_id=new_product.product_id,
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
                    color = ProductColor(
                        product_id=new_product.product_id,
                        model_id=default_model.model_id,
                        name=color_name,
                        stock_quantity=int(color_stock),
                        price=float(color_price),
                        original_price=float(color_original_price) if color_original_price else None,
                        threshold=int(threshold)
                    )
                    db.session.add(color)
                    db.session.commit()

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
            models_count = int(request.form.get('models_count', 0))
            for i in range(models_count):
                model_name = request.form.get(f'model_name_{i}')
                model_description = request.form.get(f'model_description_{i}')

                if model_name and model_description:
                    model = ProductModel(
                        product_id=new_product.product_id,
                        name=model_name,
                        description=model_description
                    )
                    db.session.add(model)
                    db.session.commit()

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
                            db.session.commit()

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
        


            
        hsn_code = ""
        if hsn_id:
            hsn_code = db.session.query(HSN.hsn_code).filter(HSN.hsn_id == hsn_id).scalar() or "NA"
        else:
            hsn_code = "NA"

        # Format the SKU ID
        sku_id = f"{category_id}-{subcategory_id}-{hsn_code}-{new_product.product_id}"

        # Update the product with the SKU ID
        new_product.sku_id = sku_id


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



@products_bp.route('/hsn/add', methods=['POST'])
@token_required(roles=['admin'])
def add_hsn():
    try:
        data = request.get_json()  # Accept JSON data
        hsn_code = data.get('hsn_code')
        description = data.get('description')
        gst_rate = data.get('gst_rate', None)  # Default to None if gst_rate is not provided

        # Log the received HSN code and description
        print(f"Received HSN Code: {hsn_code}, Description: {description}")

        if not hsn_code or not description:
            return jsonify({'message': 'HSN code and description are required'}), 400

        # Check if the HSN code already exists
        existing_hsn = HSN.query.filter_by(hsn_code=hsn_code).first()
        if existing_hsn:
            return jsonify({'message': 'HSN code already exists'}), 400

        new_hsn = HSN(hsn_code=hsn_code, hsn_description=description, gst_rate=gst_rate)
        db.session.add(new_hsn)
        db.session.commit()

        # Log the success of HSN addition
        print(f"HSN Code '{hsn_code}' added successfully!")

        return jsonify({
            'message': 'HSN added successfully!',
            'hsn_id': new_hsn.hsn_id,
            'hsn_code': new_hsn.hsn_code,
            'description': new_hsn.hsn_description,
            'gst_rate': new_hsn.gst_rate  # Returning gst_rate to confirm
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding HSN: {str(e)}")
        return jsonify({'message': 'An error occurred while adding the HSN'}), 500

@products_bp.route('/category/add', methods=['POST'])
@token_required(roles=['admin'])
def add_category():
    try:
        name = request.form.get('name')
        image = request.files.get('image')

        if not name:
            return jsonify({'message': 'Category name is required'}), 400
            
        existing_category = Category.query.filter(func.lower(Category.name) == name.lower()).first()
        if existing_category:
            return jsonify({'message': 'Category name already exists'}), 400   

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
            
        existing_subcategory = Subcategory.query.filter(
            func.lower(Subcategory.name) == name.lower(),
            Subcategory.category_id == category_id
        ).first()
        if existing_subcategory:
            return jsonify({'message': 'Subcategory name already exists in this category'}), 400
        
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
            db.joinedload(Product.sub_category),
            db.joinedload(Product.hsn),
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
                'hsn': product.hsn.hsn_code if product.hsn else None,
                'sku_id': product.sku_id,
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
                        'threshold': color.threshold,
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
                        'threshold': color.threshold,
                        'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in color.images]
                    }
                    product_dict['colors'].append(color_dict)
            
            products_list.append(product_dict)

        return jsonify(products_list)

    except Exception as e:
        logger.error(f"Error getting products by category: {str(e)}")
        return jsonify({'error': str(e)}), 500


from datetime import datetime





# Update an entire product (PUT)
@products_bp.route('/<int:product_id>', methods=['PUT'])
@token_required(roles=['admin'])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.form.to_dict() if request.form else request.json
    
    # Update basic product information
    product.name = data.get('name', product.name)
    product.description = data.get('description', product.description)
    product.category_id = data.get('category_id', product.category_id)
    product.subcategory_id = data.get('subcategory_id', product.subcategory_id)
    product.hsn_id = data.get('hsn_id', product.hsn_id)
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
@token_required(roles=['admin'])
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
    if 'hsn_id' in data:
        product.hsn_id = data['hsn_id']
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
@token_required(roles=['admin'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Get all image paths to delete files from filesystem
    image_paths = []
    for image in product.images:
        if image.image_url and not image.image_url.startswith('http'):
            image_paths.append(image.image_url.replace('/product_images/', ''))
    
    try:
        CartItem.query.filter_by(product_id=product_id).delete()
        WishlistItem.query.filter_by(product_id=product_id).delete()
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
@token_required(roles=['admin'])
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
@token_required(roles=['admin'])
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
@token_required(roles=['admin'])
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
@token_required(roles=['admin'])
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
@token_required(roles=['admin'])
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
@token_required(roles=['admin'])
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
@token_required(roles=['admin'])
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
@token_required(roles=['admin'])
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
@products_bp.route('/<int:product_id>/colors/<int:color_id>', methods=['PUT'])
@token_required(roles=['admin'])
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
@token_required(roles=['admin'])
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

@products_bp.route('/<int:product_id>/specifications', methods=['POST'])
@token_required(roles=['admin'])
def add_product_specification(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.form.to_dict() if request.form else request.json
    
    new_spec = ProductSpecification(
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
@token_required(roles=['admin'])
def update_product_specification(product_id, spec_id):
    spec = ProductSpecification.query.get_or_404(spec_id)
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
@token_required(roles=['admin'])
def delete_product_specification(product_id, spec_id):
    spec = ProductSpecification.query.get_or_404(spec_id)
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
@token_required(roles=['admin'])
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
@token_required(roles=['admin'])
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
@token_required(roles=['admin'])
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
@token_required(roles=['admin'])
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

@products_bp.route('/product/get/productstatus', methods=['GET'])
@token_required(roles=['admin'])
def get_product_status():
    results = []

    products = Product.query.all()

    for product in products:
        for model in product.models:
            for color in model.colors:
                images = ProductImage.query.filter_by(product_id=product.product_id).all()
                image_urls = [img.image_url for img in images]

                # This needs to be inside the color loop
                status='IN_STOCK'

                if(color.stock_quantity<=color.threshold):
                    status='LOW_STOCK'
                
                if(color.stock_quantity==0):
                      status='OUT_OF_STOCK'
                
                results.append({
                    "product_id": product.product_id,
                    "product_name": product.name,
                    "model_id": model.model_id,
                    "model_name": model.name,
                    "color_id": color.color_id,
                    "color_name": color.name,
                    "images": image_urls,
                    "stock_quantity": color.stock_quantity,
                    "threshold": color.threshold,
                    "status":status
                })
                


    return jsonify(results), 200


@products_bp.route('/<int:product_id>/update-all', methods=['POST'])
@token_required(roles=['admin'])
def update_all_product_data(product_id):
    """Combined endpoint to update all product data in a single request"""
    product = Product.query.get_or_404(product_id)
    
    # Get form data or JSON data
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Handle form data with potential file uploads
        data = json.loads(request.form.get('productData', '{}'))
        files = request.files.getlist('images')
        color_images = {}
        
        # Process color images from request
        for key in request.files:
            if key.startswith('color_image_'):
                color_id = key.split('_')[-1]
                if color_id not in color_images:
                    color_images[color_id] = []
                color_images[color_id].append(request.files[key])
    else:
        # Handle JSON data
        data = request.json
        files = []
        color_images = {}
    
    try:
        # Start transaction
        db.session.begin_nested()
        
        # 1. Update basic product information
        if 'basic' in data:
            basic_data = data['basic']
            product.name = basic_data.get('name', product.name)
            product.description = basic_data.get('description', product.description)
            product.category_id = basic_data.get('category_id', product.category_id)
            product.subcategory_id = basic_data.get('subcategory_id', product.subcategory_id)
            product.product_type = basic_data.get('product_type', product.product_type)
            product.updated_at = datetime.utcnow()
        
        # 2. Process specifications
        if 'specifications' in data:
            specs_data = data['specifications']
            
            # Handle spec updates and additions
            existing_spec_ids = {spec.spec_id for spec in product.specifications}
            processed_spec_ids = set()
            
            for spec_item in specs_data:
                spec_id = spec_item.get('spec_id')
                
                if spec_id and spec_id in existing_spec_ids:
                    # Update existing spec
                    spec = ModelSpecification.query.get(spec_id)
                    spec.key = spec_item.get('key', spec.key)
                    spec.value = spec_item.get('value', spec.value)
                    processed_spec_ids.add(spec_id)
                elif not spec_id:
                    # Add new spec
                    new_spec = ModelSpecification(
                        product_id=product_id,
                        key=spec_item.get('key'),
                        value=spec_item.get('value')
                    )
                    db.session.add(new_spec)
            
            # Delete specs not included in the update
            specs_to_delete = existing_spec_ids - processed_spec_ids
            for spec_id in specs_to_delete:
                spec = ModelSpecification.query.get(spec_id)
                db.session.delete(spec)
        
        # 3. Process color variants
        if 'colors' in data:
            colors_data = data['colors']
            
            # Handle color updates and additions
            existing_color_ids = {color.color_id for color in product.colors}
            processed_color_ids = set()
            
            for color_item in colors_data:
                color_id = color_item.get('color_id')
                
                if color_id and color_id in existing_color_ids:
                    # Update existing color
                    color = ProductColor.query.get(color_id)
                    color.name = color_item.get('name', color.name)
                    color.price = color_item.get('price', color.price)
                    color.original_price = color_item.get('original_price', color.original_price)
                    color.stock_quantity = color_item.get('stock_quantity', color.stock_quantity)
                    color.threshold = color_item.get('threshold', color.threshold)
                    color.model_id = color_item.get('model_id', color.model_id)
                    processed_color_ids.add(color_id)
                elif not color_id:
                    # Add new color
                    new_color = ProductColor(
                        product_id=product_id,
                        name=color_item.get('name'),
                        price=color_item.get('price'),
                        original_price=color_item.get('original_price'),
                        stock_quantity=color_item.get('stock_quantity', 0),
                        threshold=color_item.get('threshold', 10),
                        model_id=color_item.get('model_id')
                    )
                    db.session.add(new_color)
                    db.session.flush()  # Flush to get the new color ID
                    
                    # If this is a new color with a temp_id, store mapping for image processing
                    if 'temp_id' in color_item:
                        color_item['color_id'] = new_color.color_id
            
            # Delete colors not included in the update
            colors_to_delete = existing_color_ids - processed_color_ids
            for color_id in colors_to_delete:
                color = ProductColor.query.get(color_id)
                db.session.delete(color)
        
        # 4. Process main product images
        if 'images_to_delete' in data:
            # Delete images that were removed
            for image_id in data['images_to_delete']:
                image = ProductImage.query.get(image_id)
                if image and image.product_id == product_id:
                    # Get image path to delete file from filesystem
                    image_path = None
                    if image.image_url and not image.image_url.startswith('http'):
                        image_path = image.image_url.replace('/product_images/', '')
                    
                    # Delete database record
                    db.session.delete(image)
                    db.session.flush()
                    
                    # Delete file from filesystem
                    if image_path:
                        try:
                            file_path = os.path.join(UPLOAD_FOLDER, image_path)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception as e:
                            # Log error but continue
                            print(f"Error deleting file {image_path}: {str(e)}")
        
        # 5. Upload new images
        for file in files:
            if file and file.filename:
                image_url = save_image(file)
                
                if image_url:
                    # Create new product image record
                    new_image = ProductImage(
                        product_id=product_id,
                        image_url=image_url
                    )
                    db.session.add(new_image)
        
        # 6. Process color images
        for color_id, color_files in color_images.items():
            # For new colors, we need to map temp_id to actual color_id
            if not color_id.isdigit():
                # Find the corresponding color by temp_id
                for color_item in data.get('colors', []):
                    if str(color_item.get('temp_id')) == color_id and 'color_id' in color_item:
                        actual_color_id = color_item['color_id']
                        for file in color_files:
                            if file and file.filename:
                                image_url = save_image(file)
                                if image_url:
                                    new_image = ProductImage(
                                        product_id=product_id,
                                        color_id=actual_color_id,
                                        image_url=image_url
                                    )
                                    db.session.add(new_image)
            else:
                # For existing colors, use the color_id directly
                for file in color_files:
                    if file and file.filename:
                        image_url = save_image(file)
                        if image_url:
                            new_image = ProductImage(
                                product_id=product_id,
                                color_id=int(color_id),
                                image_url=image_url
                            )
                            db.session.add(new_image)
        
        # 7. Process models if needed
        if 'models' in data:
            models_data = data['models']
            
            # Handle model updates and additions
            existing_model_ids = {model.model_id for model in product.models}
            processed_model_ids = set()
            
            for model_item in models_data:
                model_id = model_item.get('model_id')
                
                if model_id and model_id in existing_model_ids:
                    # Update existing model
                    model = ProductModel.query.get(model_id)
                    model.name = model_item.get('name', model.name)
                    model.description = model_item.get('description', model.description)
                    processed_model_ids.add(model_id)
                elif not model_id:
                    # Add new model
                    new_model = ProductModel(
                        product_id=product_id,
                        name=model_item.get('name'),
                        description=model_item.get('description')
                    )
                    db.session.add(new_model)
            
            # Delete models not included in the update
            models_to_delete = existing_model_ids - processed_model_ids
            for model_id in models_to_delete:
                model = ProductModel.query.get(model_id)
                db.session.delete(model)
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'message': 'Product updated successfully',
            'product_id': product.product_id
        }), 200
    
    except Exception as e:
        # Rollback in case of any error
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

    return jsonify(results), 200
    
# CATEGORY AND SUBCATEGORY UPDATE 

    return jsonify(results), 200



# Update product category
@products_bp.route('/product/<int:product_id>/category', methods=['PUT'])
@token_required(roles=['admin'])
def update_product_category(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        data = request.json
        
        category_id = data.get('category_id')
        if not category_id:
            return jsonify({'error': 'Category ID is required'}), 400
            
        # Verify the category exists
        category = Category.query.get(category_id)
        if not category:
            return jsonify({'error': 'Category not found'}), 404
            
        # Update the category
        product.category_id = category_id
        # When changing category, reset subcategory if it doesn't belong to the new category
        if product.subcategory_id:
            subcategory = Subcategory.query.get(product.subcategory_id)
            if subcategory and subcategory.category_id != category_id:
                product.subcategory_id = None
        
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Product category updated by admin: {request.current_user.email} - Product ID: {product_id}")
        
        return jsonify({
            'message': 'Product category updated successfully',
            'product_id': product.product_id,
            'category_id': product.category_id,
            'category_name': category.name
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating product category: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Update product subcategory
@products_bp.route('/product/<int:product_id>/subcategory', methods=['PUT'])
@token_required(roles=['admin'])
def update_product_subcategory(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        data = request.json
        
        subcategory_id = data.get('subcategory_id')
        if subcategory_id is None:  # Allow setting to null/None
            product.subcategory_id = None
        else:
            # Verify the subcategory exists and belongs to the product's category
            subcategory = Subcategory.query.get(subcategory_id)
            if not subcategory:
                return jsonify({'error': 'Subcategory not found'}), 404
                
            if subcategory.category_id != product.category_id:
                return jsonify({'error': 'Subcategory does not belong to the product\'s category'}), 400
                
            product.subcategory_id = subcategory_id
        
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Product subcategory updated by admin: {request.current_user.email} - Product ID: {product_id}")
        
        return jsonify({
            'message': 'Product subcategory updated successfully',
            'product_id': product.product_id,
            'subcategory_id': product.subcategory_id,
            'subcategory_name': Subcategory.query.get(product.subcategory_id).name if product.subcategory_id else None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating product subcategory: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Update both category and subcategory in one request
@products_bp.route('/product/<int:product_id>/categorization', methods=['PUT'])
@token_required(roles=['admin'])
def update_product_categorization(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        data = request.json
        
        category_id = data.get('category_id')
        subcategory_id = data.get('subcategory_id')
        
        if not category_id:
            return jsonify({'error': 'Category ID is required'}), 400
            
        # Verify the category exists
        category = Category.query.get(category_id)
        if not category:
            return jsonify({'error': 'Category not found'}), 404
            
        # Update the category
        product.category_id = category_id
        
        # Handle subcategory
        if subcategory_id:
            # Verify the subcategory exists and belongs to the selected category
            subcategory = Subcategory.query.get(subcategory_id)
            if not subcategory:
                return jsonify({'error': 'Subcategory not found'}), 404
                
            if subcategory.category_id != category_id:
                return jsonify({'error': 'Subcategory does not belong to the selected category'}), 400
                
            product.subcategory_id = subcategory_id
        else:
            # If no subcategory provided, set to None
            product.subcategory_id = None
        
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Product categorization updated by admin: {request.current_user.email} - Product ID: {product_id}")
        
        response = {
            'message': 'Product categorization updated successfully',
            'product_id': product.product_id,
            'category_id': product.category_id,
            'category_name': category.name,
            'subcategory_id': product.subcategory_id
        }
        
        if product.subcategory_id:
            response['subcategory_name'] = Subcategory.query.get(product.subcategory_id).name
        
        return jsonify(response), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating product categorization: {str(e)}")

        return jsonify({'error': str(e)}), 500


# Update product HSN code
@products_bp.route('/update/<int:product_id>/hsn', methods=['PUT'])
@token_required(roles=['admin'])
def update_product_hsn(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        data = request.json
        
        hsn_id = data.get('hsn_id')
        if not hsn_id:
            return jsonify({'error': 'HSN ID is required'}), 400
            
        # Verify the HSN exists
        hsn = HSN.query.get(hsn_id)
        if not hsn:
            return jsonify({'error': 'HSN code not found'}), 404
            
        # Update the HSN
        product.hsn_id = hsn_id
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Product HSN updated by admin: {request.current_user.email} - Product ID: {product_id}")
        
        return jsonify({
            'message': 'Product HSN updated successfully',
            'product_id': product.product_id,
            'hsn_id': product.hsn_id,
            'hsn_code': hsn.hsn_code,
            'hsn_description': hsn.hsn_description
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating product HSN: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Edit existing HSN entry
@products_bp.route('/edit/hsn/<int:hsn_id>', methods=['PUT'])
@token_required(roles=['admin'])
def edit_hsn(hsn_id):
    try:
        hsn = HSN.query.get_or_404(hsn_id)
        data = request.get_json()
        
        hsn_code = data.get('hsn_code')
        description = data.get('description')
        gst_rate = data.get('gst_rate')
        
        if not hsn_code or not description:
            return jsonify({'message': 'HSN code and description are required'}), 400

        # Check if the new HSN code already exists (excluding current record)
        existing_hsn = HSN.query.filter(
            HSN.hsn_code == hsn_code,
            HSN.hsn_id != hsn_id
        ).first()
        
        if existing_hsn:
            return jsonify({'message': 'HSN code already exists'}), 400

        # Update the HSN record
        hsn.hsn_code = hsn_code
        hsn.hsn_description = description
        hsn.gst_rate = gst_rate
        
        db.session.commit()
        
        logger.info(f"HSN code updated by admin: {request.current_user.email} - HSN ID: {hsn_id}")
        
        return jsonify({
            'message': 'HSN updated successfully!',
            'hsn_id': hsn.hsn_id,
            'hsn_code': hsn.hsn_code,
            'description': hsn.hsn_description,
            'gst_rate': hsn.gst_rate
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating HSN: {str(e)}")
        return jsonify({'message': 'An error occurred while updating the HSN'}), 500

# EDIT CATEGORY AND SUBCATEGORY

#  CATEGORY 
@products_bp.route('/category/<int:category_id>', methods=['PUT'])
@token_required(roles=['admin'])
def update_category(category_id):
    try:
        data = request.json
        category = Category.query.get_or_404(category_id)

        name = data.get('name')
        image_url = data.get('image_url')

        if name:
            category.name = name
        if image_url:
            category.image_url = image_url

        db.session.commit()
        logger.info(f"Category updated by admin: {request.current_user.email} - Category ID: {category_id}")

        return jsonify({
            'message': 'Category updated successfully',
            'category_id': category.category_id,
            'name': category.name,
            'image_url': category.image_url
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating category: {str(e)}")
        return jsonify({'error': str(e)}), 500


# # SUBCATEGORY 

@products_bp.route('/subcategory/<int:subcategory_id>', methods=['PUT'])
@token_required(roles=['admin'])
def update_subcategory(subcategory_id):
    try:
        data = request.json
        subcategory = Subcategory.query.get_or_404(subcategory_id)

        name = data.get('name')
        if name:
            subcategory.name = name

        db.session.commit()
        logger.info(f"Subcategory updated by admin: {request.current_user.email} - Subcategory ID: {subcategory_id}")

        return jsonify({
            'message': 'Subcategory updated successfully',
            'subcategory_id': subcategory.subcategory_id,
            'name': subcategory.name
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating subcategory: {str(e)}")
        return jsonify({'error': str(e)}), 500


# DELETE Category AND SUBCATEGORY 


# Delete a category

@products_bp.route('/delete/category/<int:category_id>', methods=['DELETE'])
@token_required(roles=['admin'])
def delete_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)

        # Check if any product is using this category
        product_using_category = Product.query.filter_by(category_id=category_id).first()
        if product_using_category:
            return jsonify({'error': 'Cannot delete. Category is assigned to one or more products.'}), 400

        db.session.delete(category)
        db.session.commit()
        logger.info(f"Category deleted by admin: {request.current_user.email} - Category ID: {category_id}")
        return jsonify({'message': 'Category deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting category: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


 # Delete a subcategory

@products_bp.route('/delete/subcategory/<int:subcategory_id>', methods=['DELETE'])
@token_required(roles=['admin'])
def delete_subcategory(subcategory_id):
    try:
        subcategory = Subcategory.query.get_or_404(subcategory_id)

        # Check if any product is using this subcategory
        product_using_subcategory = Product.query.filter_by(subcategory_id=subcategory_id).first()
        if product_using_subcategory:
            return jsonify({'error': 'Cannot delete. Subcategory is assigned to one or more products.'}), 400

        db.session.delete(subcategory)
        db.session.commit()
        logger.info(f"Subcategory deleted by admin: {request.current_user.email} - Subcategory ID: {subcategory_id}")
        return jsonify({'message': 'Subcategory deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting subcategory: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    



# Delete HSN code
@products_bp.route('/delete/hsn/<int:hsn_id>', methods=['DELETE'])
@token_required(roles=['admin'])
def delete_hsn(hsn_id):
    try:
        hsn = HSN.query.get_or_404(hsn_id)

        # Check if any product is using this HSN
        product_using_hsn = Product.query.filter_by(hsn_id=hsn_id).first()
        if product_using_hsn:
            return jsonify({'error': 'Cannot delete. HSN code is assigned to one or more products.'}), 400

        db.session.delete(hsn)
        db.session.commit()
        
        logger.info(f"HSN code deleted by admin: {request.current_user.email} - HSN ID: {hsn_id}")
        return jsonify({'message': 'HSN code deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting HSN code: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@products_bp.route('/product/slug/<product_slug>', methods=['GET'])
def get_product_by_slug(product_slug):
    try:
        # First try to find by ID if slug is numeric
        if product_slug.isdigit():
            product = Product.query.options(
                db.joinedload(Product.images),
                db.joinedload(Product.main_category),
                db.joinedload(Product.sub_category),
                db.joinedload(Product.hsn),
                db.joinedload(Product.models).joinedload(ProductModel.colors).joinedload(ProductColor.images),
                db.joinedload(Product.models).joinedload(ProductModel.specifications),
                db.joinedload(Product.colors).joinedload(ProductColor.images)
            ).get(product_slug)
            if product:
                # Use the same serialization logic as below instead of to_dict()
                product_dict = {
                    'product_id': product.product_id,
                    'name': product.name,
                    'description': product.description,
                    'category': getattr(product.main_category, 'name', None),
                    'subcategory': getattr(product.sub_category, 'name', None),
                    'hsn_id': getattr(getattr(product, 'hsn', None), 'hsn_code', None),
                    'product_type': product.product_type,
                    'rating': product.rating,
                    'raters': product.raters,
                    'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in product.images],
                    'specifications': [{'spec_id': s.spec_id, 'key': s.key, 'value': s.value} for s in product.specifications],
                    'models': [],
                    'colors': []
                }
                
                # Add models data if exists
                for model in product.models:
                    model_dict = {
                        'model_id': model.model_id,
                        'name': model.name,
                        'description': model.description,
                        'colors': [],
                        'specifications': [{'spec_id': s.spec_id, 'key': s.key, 'value': s.value} for s in model.specifications]
                    }
                    
                    for color in model.colors:
                        color_dict = {
                            'color_id': color.color_id,
                            'name': color.name,
                            'stock_quantity': color.stock_quantity,
                            'price': float(color.price),
                            'original_price': float(color.original_price) if color.original_price else None,
                            'threshold': color.threshold,
                            'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in color.images]
                        }
                        model_dict['colors'].append(color_dict)
                    
                    product_dict['models'].append(model_dict)
                
                # Add colors for single product type
                if product.product_type == 'single':
                    for color in product.colors:
                        color_dict = {
                            'color_id': color.color_id,
                            'name': color.name,
                            'stock_quantity': color.stock_quantity,
                            'price': float(color.price),
                            'original_price': float(color.original_price) if color.original_price else None,
                            'threshold': color.threshold,
                            'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in color.images]
                        }
                        product_dict['colors'].append(color_dict)
                
                return jsonify(product_dict)
        
        # Otherwise search by name (with hyphens replaced by spaces)
        name = unquote(product_slug).replace('-', ' ')
        product = Product.query.options(
            db.joinedload(Product.images),
            db.joinedload(Product.main_category),
            db.joinedload(Product.sub_category),
            db.joinedload(Product.hsn),
            db.joinedload(Product.models).joinedload(ProductModel.colors).joinedload(ProductColor.images),
            db.joinedload(Product.models).joinedload(ProductModel.specifications),
            db.joinedload(Product.colors).joinedload(ProductColor.images)
        ).filter(
            func.replace(Product.name, '-', ' ').ilike(f'%{name}%')
        ).first()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Use the same serialization logic as your product_detail endpoint
        product_dict = {
            'product_id': product.product_id,
            'name': product.name,
            'description': product.description,
            'category': getattr(product.main_category, 'name', None),
            'subcategory': getattr(product.sub_category, 'name', None),
            'hsn_id': getattr(getattr(product, 'hsn', None), 'hsn_code', None),
            'product_type': product.product_type,
            'rating': product.rating,
            'raters': product.raters,
            'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in product.images],
            'specifications': [{'spec_id': s.spec_id, 'key': s.key, 'value': s.value} for s in product.specifications],
            'models': [],
            'colors': []
        }
        
        # Add models data if exists
        for model in product.models:
            model_dict = {
                'model_id': model.model_id,
                'name': model.name,
                'description': model.description,
                'colors': [],
                'specifications': [{'spec_id': s.spec_id, 'key': s.key, 'value': s.value} for s in model.specifications]
            }
            
            for color in model.colors:
                color_dict = {
                    'color_id': color.color_id,
                    'name': color.name,
                    'stock_quantity': color.stock_quantity,
                    'price': float(color.price),
                    'original_price': float(color.original_price) if color.original_price else None,
                    'threshold': color.threshold,
                    'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in color.images]
                }
                model_dict['colors'].append(color_dict)
            
            product_dict['models'].append(model_dict)
        
        # Add colors for single product type
        if product.product_type == 'single':
            for color in product.colors:
                color_dict = {
                    'color_id': color.color_id,
                    'name': color.name,
                    'stock_quantity': color.stock_quantity,
                    'price': float(color.price),
                    'original_price': float(color.original_price) if color.original_price else None,
                    'threshold': color.threshold,
                    'images': [{'image_id': img.image_id, 'image_url': img.image_url} for img in color.images]
                }
                product_dict['colors'].append(color_dict)
        
        return jsonify(product_dict)
        
    except Exception as e:
        logger.error(f"Error getting product by slug {product_slug}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

        
# Update cover image (special case of updating the first image)
@products_bp.route('/<int:product_id>/cover-image', methods=['POST'])
def update_cover_image(product_id):
    # Get the first image for this product (lowest image_id)
    first_image = ProductImage.query.filter_by(product_id=product_id)\
                                  .order_by(ProductImage.image_id.asc())\
                                  .first()
    
    if not first_image:
        return jsonify({'error': 'No images found for this product'}), 404
    
    # Check if image file is provided
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    image_file = request.files['image']
    new_image_url = save_image(image_file)
    
    if not new_image_url:
        return jsonify({'error': 'Invalid image file'}), 400
    
    # Store old path for cleanup
    old_image_path = None
    if first_image.image_url and not first_image.image_url.startswith('http'):
        old_image_path = first_image.image_url.replace('/product_images/', '')
    
    # Update the image URL
    first_image.image_url = new_image_url
    
    try:
        db.session.commit()
        
        # Delete old image file if replaced
        if old_image_path and new_image_url != f'/product_images/{old_image_path}':
            try:
                file_path = os.path.join(UPLOAD_FOLDER, old_image_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error deleting file {old_image_path}: {str(e)}")
        
        return jsonify({
            'message': 'Cover image updated successfully',
            'image_id': first_image.image_id,
            'image_url': new_image_url
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400        


@products_bp.route('/api/product-meta/<int:product_id>', methods=['GET'])
def product_meta(product_id):
    try:
        product = Product.query.options(
            db.joinedload(Product.images)
        ).get_or_404(product_id)
        
        # Get primary image URL and convert to absolute URL
        primary_image_url = ''
        if product.images and len(product.images) > 0:
            image_url = product.images[0].image_url
            
            # This is the key part - make sure we have the full domain in the URL
            if not image_url.startswith(('http://', 'https://')):
                base_url = f"https://{request.host}"  # Force https for production
                
                # If the image URL already starts with a slash, don't add another one
                if image_url.startswith('/'):
                    primary_image_url = f"{base_url}{image_url}"
                else:
                    primary_image_url = f"{base_url}/{image_url}"
            else:
                primary_image_url = image_url
        
        # For debugging
        logger.info(f"Original image URL: {product.images[0].image_url if product.images else 'None'}")
        logger.info(f"Converted image URL: {primary_image_url}")
        
        # Direct HTML rendering for meta tags
        meta_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta property="og:title" content="{product.name}">
    <meta property="og:description" content="{product.description}">
    <meta property="og:image" content="{primary_image_url}">
    <meta property="og:type" content="product">
    <meta property="og:url" content="https://mtm-store.com/products/{product.product_id}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{product.name}">
    <meta name="twitter:description" content="{product.description}">
    <meta name="twitter:image" content="{primary_image_url}">
    <title>{product.name}</title>
</head>
<body>
    <h1>{product.name}</h1>
    <p>{product.description}</p>
    <img src="{primary_image_url}" alt="{product.name}" />
</body>
</html>"""
        return meta_html, 200, {'Content-Type': 'text/html; charset=utf-8'}
    
    except Exception as e:
        logger.error(f"Error generating product meta: {str(e)}")
        return "Product not found", 404


