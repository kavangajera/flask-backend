from datetime import datetime
from extensions import db

class Order(db.Model):
    __tablename__ = 'orders'
    
    order_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id', ondelete='CASCADE'), nullable=True)
    offline_customer_id = db.Column(db.Integer, db.ForeignKey('offline_customer.customer_id', ondelete='CASCADE'), nullable=True)
    address_id = db.Column(db.Integer, db.ForeignKey('address.address_id'), nullable=False)
    total_items = db.Column(db.Integer, default=0)
    subtotal = db.Column(db.Numeric(10, 2), default=0.00)
    discount_percent = db.Column(db.Numeric(5, 2), default=0.00)
    delivery_charge = db.Column(db.Numeric(10, 2), default=0.00)
    tax_percent = db.Column(db.Numeric(5, 2), default=18.00)
    total_amount = db.Column(db.Numeric(10, 2), default=0.00)
    channel = db.Column(db.String(20), default='offline')
    payment_status = db.Column(db.String(20), default='paid')
    fulfillment_status = db.Column(db.Boolean, default=False)
    delivery_status = db.Column(db.String(20), default='intransit')
    delivery_method = db.Column(db.String(20), default='shipping')
    awb_number = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    __table_args__ = (
        db.ForeignKeyConstraint(['customer_id'], ['customer.customer_id'], ondelete='CASCADE'),
        db.ForeignKeyConstraint(['offline_customer_id'], ['offline_customer.customer_id'], ondelete='CASCADE'),
        db.CheckConstraint('customer_id IS NOT NULL OR offline_customer_id IS NOT NULL', name='check_order_customer_type'),
    )
    
    # Relationships
    customer = db.relationship('Customer', back_populates='orders')
    offline_customer = db.relationship('OfflineCustomer', back_populates='orders')
    address = db.relationship('Address', back_populates='orders')
    items = db.relationship('OrderItem', back_populates='order', cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('product_models.model_id'), nullable=True)
    color_id = db.Column(db.Integer, db.ForeignKey('product_colors.color_id'), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Relationships
    product = db.relationship('Product', backref='order_items')
    order = db.relationship('Order', back_populates='items')
    model = db.relationship('ProductModel', backref='order_items')
    color = db.relationship('ProductColor', backref='order_items')
