# # from extensions import db

# # class Product(db.Model):
# #     __tablename__ = 'product'
    
# #     product_id = db.Column(db.Integer, primary_key=True)
# #     unit = db.Column(db.Integer, default=1)
# #     rating = db.Column(db.Float)
# #     raters = db.Column(db.Integer)
# #     description = db.Column(db.Text)
# #     name = db.Column(db.String(255))
# #     category = db.Column(db.String(255))
# #     price = db.Column(db.Numeric(10, 2))
# #     deleted_price = db.Column(db.Numeric(10, 2))
    
# #     # Relationships
# #     images = db.relationship('ProductImage', backref='product', lazy=True)
# #     order_items = db.relationship('OrderHistoryItem', backref='product', lazy=True)

# # class ProductImage(db.Model):
# #     __tablename__ = 'productimages'
    
# #     image_id = db.Column(db.Integer, primary_key=True)
# #     product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'))
# #     image_url = db.Column(db.Text) 



# from extensions import db
# from datetime import datetime

# class Product(db.Model):
#     __tablename__ = 'products'
    
#     product_id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     description = db.Column(db.Text, nullable=False)
#     category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=False)
#     subcategory_id = db.Column(db.Integer, db.ForeignKey('subcategories.subcategory_id'), nullable=True)
#     product_type = db.Column(db.String(20), nullable=False)  # 'single' or 'variable'
#     rating = db.Column(db.Float, default=0)
#     raters = db.Column(db.Integer, default=0)
#     created_at = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo('Asia/Kolkata')))
#     updated_at = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo('Asia/Kolkata')), onupdate=datetime.now(tz=ZoneInfo('Asia/Kolkata')))
    

    
#     # Relationships
#     images = db.relationship('ProductImage', backref='product', lazy=True, cascade="all, delete-orphan")
#     models = db.relationship('ProductModel', backref='product', lazy=True, cascade="all, delete-orphan")
#     colors = db.relationship('ProductColor', backref='product', lazy=True, cascade="all, delete-orphan")
    
#     cart_items = db.relationship('CartItem', backref='product', lazy=True, cascade="all, delete-orphan")
#     wishlist_items = db.relationship('WishlistItem', backref='product', lazy=True, cascade="all, delete-orphan")

# class ProductImage(db.Model):
#     __tablename__ = 'product_images'
    
#     image_id = db.Column(db.Integer, primary_key=True)
#     product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=True)
#     color_id = db.Column(db.Integer, db.ForeignKey('product_colors.color_id'), nullable=True)
#     image_url = db.Column(db.String(255), nullable=False)

# class ProductModel(db.Model):
#     __tablename__ = 'product_models'
    
#     model_id = db.Column(db.Integer, primary_key=True)
#     product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
#     name = db.Column(db.String(100), nullable=False)
#     description = db.Column(db.Text, nullable=False)
    
#     # Relationships
#     colors = db.relationship('ProductColor', backref='model', lazy=True, cascade="all, delete-orphan")
#     specifications = db.relationship('ModelSpecification', backref='model', lazy=True, cascade="all, delete-orphan")

# class ProductColor(db.Model):
#     __tablename__ = 'product_colors'
    
#     color_id = db.Column(db.Integer, primary_key=True)
#     product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=True)
#     model_id = db.Column(db.Integer, db.ForeignKey('product_models.model_id'), nullable=True)
#     name = db.Column(db.String(50), nullable=False)
#     stock_quantity = db.Column(db.Integer, default=0)
#     price = db.Column(db.Numeric(10, 2), nullable=False)
#     original_price = db.Column(db.Numeric(10, 2), nullable=True)
#     threshold = db.Column(db.Integer,default=10)
#     # Relationships
#     images = db.relationship('ProductImage', backref='color', lazy=True, cascade="all, delete-orphan")




# class ModelSpecification(db.Model):
#     __tablename__ = 'model_specifications'
    
#     spec_id = db.Column(db.Integer, primary_key=True)
#     model_id = db.Column(db.Integer, db.ForeignKey('product_models.model_id'), nullable=False)
#     key = db.Column(db.String(100), nullable=False)
#     value = db.Column(db.String(255), nullable=False)

from extensions import db
from datetime import datetime
from models.review import Review
from zoneinfo import ZoneInfo

class Product(db.Model):
    __tablename__ = 'products'
    
    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=False)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('subcategories.subcategory_id'), nullable=True)
    hsn_id = db.Column(db.Integer, db.ForeignKey('hsn.hsn_id'), nullable=True)
    product_type = db.Column(db.String(20), nullable=False)  # 'single' or 'variable'
    rating = db.Column(db.Float, default=0)
    raters = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo('Asia/Kolkata')))
    updated_at = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo('Asia/Kolkata')), onupdate=datetime.now(tz=ZoneInfo('Asia/Kolkata')))
    sku_id = db.Column(db.String(100), nullable=True, unique=True)
    
    
    
    # Relationships
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade="all, delete-orphan")
    models = db.relationship('ProductModel', backref='product', lazy=True, cascade="all, delete-orphan")
    colors = db.relationship('ProductColor', backref='product', lazy=True, cascade="all, delete-orphan")
    specifications = db.relationship('ProductSpecification', backref='product', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='product', lazy=True, cascade="all, delete-orphan")

    def update_rating(self):
    
        reviews = Review.query.filter_by(product_id=self.product_id).all()
        if not reviews:
            self.rating = 0
            self.raters = 0
        else:
            total_rating = sum(review.rating for review in reviews)
            self.raters = len(reviews)
            self.rating = round(total_rating / self.raters, 1)
        
        db.session.commit()


class ProductImage(db.Model):
    __tablename__ = 'product_images'
    
    image_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=True)
    color_id = db.Column(db.Integer, db.ForeignKey('product_colors.color_id'), nullable=True)
    image_url = db.Column(db.String(255), nullable=False)

class ProductModel(db.Model):
    __tablename__ = 'product_models'
    
    model_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Relationships
    colors = db.relationship('ProductColor', backref='model', lazy=True, cascade="all, delete-orphan")
    specifications = db.relationship('ModelSpecification', backref='model', lazy=True, cascade="all, delete-orphan")

class ProductColor(db.Model):
    __tablename__ = 'product_colors'
    
    color_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=True)
    model_id = db.Column(db.Integer, db.ForeignKey('product_models.model_id'), nullable=True)
    name = db.Column(db.String(50), nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    original_price = db.Column(db.Numeric(10, 2), nullable=True)
    threshold = db.Column(db.Integer,default=10)
    # Relationships
    images = db.relationship('ProductImage', backref='color', lazy=True, cascade="all, delete-orphan")

class ProductSpecification(db.Model):
    __tablename__ = 'product_specifications'
    
    spec_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(255), nullable=False)

class ModelSpecification(db.Model):
    __tablename__ = 'model_specifications'
    
    spec_id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey('product_models.model_id'), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(255), nullable=False)