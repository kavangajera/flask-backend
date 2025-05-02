# models/address.py
from extensions import db
from datetime import datetime

class Address(db.Model):
    __tablename__ = 'address'
    
    address_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id', ondelete='CASCADE'), nullable=True)  # NULL होने दें
    offline_customer_id = db.Column(db.Integer, db.ForeignKey('offline_customer.customer_id', ondelete='CASCADE'), nullable=True)  # NULL होने दें
    
    # नए फील्ड्स
    name = db.Column(db.String(255), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    locality = db.Column(db.String(255), nullable=False)
    address_line = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey('state.state_id'), nullable=False)
    landmark = db.Column(db.String(255))
    alternate_phone = db.Column(db.String(15))
    address_type = db.Column(db.String(20), nullable=False, default='Home')
    
    # लोकेशन कोऑर्डिनेट्स
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign Keys और Constraints
    __table_args__ = (
        db.CheckConstraint('customer_id IS NOT NULL OR offline_customer_id IS NOT NULL', name='check_address_customer_type'),
    )
    
    # Relationships
    customer = db.relationship('Customer', back_populates='addresses')
    offline_customer = db.relationship('OfflineCustomer', back_populates='addresses')
    state = db.relationship('State', backref=db.backref('addresses', lazy=True))
    orders = db.relationship('Order', back_populates='address')

    def to_dict(self):
        return {
            'address_id': self.address_id,
            'customer_id': self.customer_id,
            'offline_customer_id': self.offline_customer_id,
            'name': self.name,
            'mobile': self.mobile,
            'pincode': self.pincode,
            'locality': self.locality,
            'address_line': self.address_line,
            'city': self.city,
            'state_id': self.state_id,
            'state_name': self.state.name if self.state else None,
            'state_abbreviation': self.state.abbreviation if self.state else None,
            'landmark': self.landmark,
            'alternate_phone': self.alternate_phone,
            'address_type': self.address_type,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
