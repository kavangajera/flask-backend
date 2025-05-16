from datetime import datetime
from extensions import db
from zoneinfo import ZoneInfo
class Order(db.Model):
    __tablename__ = 'orders'
    
    # New columns - explicit autoincrement
    order_index = db.Column(db.Integer, autoincrement=True, nullable=False, unique=True)
    
    # Computed order_id
    order_id = db.Column(db.String(30), primary_key=True, unique=True)  # Increased length to accommodate date

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
    upload_wbn = db.Column(db.String(50), nullable=True)
    order_status = db.Column(db.String(10), default="PENDING")
    payment_type = db.Column(db.String(20), default='cod')    
    created_at = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo('Asia/Kolkata')))
    updated_at = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo('Asia/Kolkata')), onupdate=datetime.now(tz=ZoneInfo('Asia/Kolkata')))
    
    # Foreign Keys
    __table_args__ = (
        db.ForeignKeyConstraint(['customer_id'], ['customer.customer_id'], ondelete='CASCADE'),
        db.ForeignKeyConstraint(['offline_customer_id'], ['offline_customer.customer_id'], ondelete='CASCADE'),
        db.CheckConstraint('customer_id IS NOT NULL OR offline_customer_id IS NOT NULL', name='check_order_customer_type'),
    )
    
    # Modified generate_order_id method
    def generate_order_id(self):
        if not self.order_index:
            raise ValueError("order_index must be set before generating order_id")
        date_str = self.created_at.strftime('%d-%m-%Y')
        return f"{date_str}#{self.order_index}"
    
    # Modified __init__ method - does not set order_id automatically
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Note: No longer automatically setting order_id here 
        # This should be done explicitly after setting order_index
    
    # Relationships
    customer = db.relationship('Customer', back_populates='orders')
    offline_customer = db.relationship('OfflineCustomer', back_populates='orders')
    address = db.relationship('Address', back_populates='orders')
    items = db.relationship('OrderItem', back_populates='order', cascade="all, delete-orphan")
    details = db.relationship('OrderDetail', back_populates='order', cascade="all, delete-orphan", passive_deletes=True)


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(30), db.ForeignKey('orders.order_id'), nullable=False)  # Increased length
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
    serial_numbers = db.relationship('SerialNumber', back_populates='order_item', cascade="all, delete-orphan")
    details = db.relationship('OrderDetail', back_populates='item', cascade="all, delete-orphan", passive_deletes=True)


class SerialNumber(db.Model):
    __tablename__ = 'serial_numbers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_id = db.Column(db.Integer, db.ForeignKey('order_items.item_id', ondelete='CASCADE'), nullable=False)
    sr_number = db.Column(db.String(50), nullable=True)
    
    # Relationship
    order_item = db.relationship('OrderItem', back_populates='serial_numbers')


class OrderDetail(db.Model):
    __tablename__ = 'order_details'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('order_items.item_id', ondelete='CASCADE'), nullable=False)
    sr_no = db.Column(db.String(250), nullable=True)
    order_id = db.Column(db.String(30), db.ForeignKey('orders.order_id', ondelete='CASCADE'), nullable=False)  # Increased length
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False)
    
   # Fixed relationships
    item = db.relationship('OrderItem', back_populates='details')
    order = db.relationship('Order', back_populates='details')
    product = db.relationship('Product', backref='order_details')


class OrderStatusHistory(db.Model):
    __tablename__ = 'order_status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(30), db.ForeignKey('orders.order_id'))
    changed_by = db.Column(db.String(50))  # or db.Text if longer
    from_status = db.Column(db.String(255))  # Previous states
    to_status = db.Column(db.String(255))    # New states
    change_reason = db.Column(db.String(255))
    changed_at = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo('Asia/Kolkata')))
    
    # Relationship
    order = db.relationship('Order', backref='status_history')