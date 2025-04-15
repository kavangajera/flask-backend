# models/address.py
from extensions import db

class Address(db.Model):
    __tablename__ = 'addresses'
    
    address_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=True)  # NULL हो सकता है
    offline_customer_id = db.Column(db.Integer, nullable=True)  # NULL हो सकता है
    street = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(20), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    
    # Foreign Keys
    __table_args__ = (
        db.ForeignKeyConstraint(['customer_id'], ['customer.customer_id'], ondelete='CASCADE'),
        db.ForeignKeyConstraint(['offline_customer_id'], ['offline_customer.customer_id'], ondelete='CASCADE'),
        db.CheckConstraint('customer_id IS NOT NULL OR offline_customer_id IS NOT NULL', name='check_customer_type')
    )
    
    # Relationships
    customer = db.relationship('Customer', back_populates='addresses')
    offline_customer = db.relationship('OfflineCustomer', back_populates='addresses')
