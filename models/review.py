from datetime import datetime
from extensions import db

class Review(db.Model):
    __tablename__ = 'reviews'
    
    review_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Rating from 1-5
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('Customer', backref='reviews')
    
    # Add a unique constraint to ensure one review per product per customer
    __table_args__ = (
        db.UniqueConstraint('product_id', 'customer_id', name='uq_customer_product_review'),
    )
    
    def to_dict(self):
        return {
            'review_id': self.review_id,
            'product_id': self.product_id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name,
            'rating': self.rating,
            'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }