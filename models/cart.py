from extensions import db
from datetime import datetime

class Cart(db.Model):
    __tablename__ = 'carts'
    
    cart_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id'), nullable=False)
    total_cart_price = db.Column(db.Numeric(10, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with Customer
    customer = db.relationship('Customer', backref='cart', lazy=True)
    
    # Relationship with CartItem - one cart can have many items
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade="all, delete-orphan")

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    item_id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.cart_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('product_models.model_id'), nullable=True)
    spec_id = db.Column(db.Integer, db.ForeignKey('product_specifications.spec_id'), nullable=True)
    color_id = db.Column(db.Integer, db.ForeignKey('product_colors.color_id'), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    total_item_price = db.Column(db.Numeric(10, 2), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships with related tables
    product = db.relationship('Product', backref='cart_items')
    model = db.relationship('ProductModel', backref='cart_items')
    specification = db.relationship('ProductSpecification', backref='cart_items')
    color = db.relationship('ProductColor', backref='cart_items')