from datetime import datetime
from extensions import db

class OrderHistory(db.Model):
    __tablename__ = 'orderhistory'
    
    order_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id'))
    address = db.Column(db.Text)
    date_time = db.Column(db.DateTime, default=lambda: datetime.now())
    num_products = db.Column(db.Integer)
    total_price = db.Column(db.Numeric(10, 2))
    delivery_charge = db.Column(db.Numeric(10, 2))
    final_payment = db.Column(db.Numeric(10, 2))
    
    # Relationship with OrderHistoryItem
    items = db.relationship('OrderHistoryItem', backref='order', lazy=True)

class OrderHistoryItem(db.Model):
    __tablename__ = 'orderhistoryitems'
    
    item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orderhistory.order_id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'))
    quantity = db.Column(db.Integer)
    product_price = db.Column(db.Numeric(10, 2)) 
