from flask_login import UserMixin
from extensions import db

class OfflineCustomer(UserMixin, db.Model):
    __tablename__ = 'offline_customer'
    
    customer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    mobile = db.Column(db.String(15), unique=True, nullable=True)
    email = db.Column(db.String(255), unique=True)
    
    
    role = db.Column(db.String(20), default='offline_customer')

    # Google Auth fields
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    
    
    # Relationships
    orders = db.relationship('Order', back_populates='offline_customer', lazy=True, cascade="all, delete-orphan")
    addresses = db.relationship('Address', back_populates='offline_customer', lazy=True, cascade="all, delete-orphan")
    
    def get_id(self):
        return str(self.customer_id)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_google_user(self):
        return self.google_id is not None
    
    def get_dict(self):
        return {
            'customer_id': self.customer_id,
            'name': self.name,
            'mobile': self.mobile,
            'email': self.email,
            'role': self.role,
            'google_id': self.google_id,
            
        } 