from extensions import db
from datetime import datetime
from zoneinfo import ZoneInfo
class Wishlist(db.Model):
    __tablename__ = 'wishlists'
    
    wishlist_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo('Asia/Kolkata')))
    updated_at = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo('Asia/Kolkata')), onupdate=datetime.now(tz=ZoneInfo('Asia/Kolkata')))
    
    # Relationship with Customer
    customer = db.relationship('Customer', backref='wishlist', lazy=True)
    
    # Relationship with WishlistItem - one wishlist can have many items
    items = db.relationship('WishlistItem', backref='wishlist', lazy=True, cascade="all, delete-orphan")

class WishlistItem(db.Model):
    __tablename__ = 'wishlist_items'
    
    item_id = db.Column(db.Integer, primary_key=True)
    wishlist_id = db.Column(db.Integer, db.ForeignKey('wishlists.wishlist_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('product_models.model_id'), nullable=True)
    color_id = db.Column(db.Integer, db.ForeignKey('product_colors.color_id'), nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo('Asia/Kolkata')))
    
    # Relationships with related tables
    # product = db.relationship('Product', backref='wishlist_items', lazy=True)
    model = db.relationship('ProductModel', backref='wishlist_items')
    
    color = db.relationship('ProductColor', backref='wishlist_items')