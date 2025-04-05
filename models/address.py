# models/address.py
from extensions import db
from datetime import datetime

class Address(db.Model):
    __tablename__ = 'address'
    
    address_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    locality = db.Column(db.String(255), nullable=False)
    address_line = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey('state.state_id'), nullable=False)
    landmark = db.Column(db.String(255), nullable=True)
    alternate_phone = db.Column(db.String(15), nullable=True)
    address_type = db.Column(db.String(20), nullable=False)  # 'Home' or 'Work'
    
    # For location coordinates from "Use my current location"
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    state = db.relationship('State', backref=db.backref('addresses', lazy=True))


    def to_dict(self):
        return {
            'address_id': self.address_id,
            'customer_id': self.customer_id,
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
            'longitude': self.longitude
        }
