from flask_login import UserMixin
from extensions import db

class Customer(UserMixin, db.Model):
    __tablename__ = 'customer'
    
    customer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    mobile = db.Column(db.String(15), unique=True, nullable=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    role = db.Column(db.String(20), default='customer')

    # Google Auth fields
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    
    # Relationships
    orders = db.relationship('Order', back_populates='customer', lazy=True, cascade="all, delete-orphan")
    addresses = db.relationship('Address', back_populates='customer', lazy=True, cascade="all, delete-orphan")
    
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
            'age':self.age,
            'gender':self.gender
            
        }