from extensions import db

class Product(db.Model):
    __tablename__ = 'product'
    
    product_id = db.Column(db.Integer, primary_key=True)
    unit = db.Column(db.Integer, default=1)
    rating = db.Column(db.Float)
    raters = db.Column(db.Integer)
    description = db.Column(db.Text)
    name = db.Column(db.String(255))
    category = db.Column(db.String(255))
    price = db.Column(db.Numeric(10, 2))
    deleted_price = db.Column(db.Numeric(10, 2))
    
    # Relationships
    images = db.relationship('ProductImage', backref='product', lazy=True)
    order_items = db.relationship('OrderHistoryItem', backref='product', lazy=True)

class ProductImage(db.Model):
    __tablename__ = 'productimages'
    
    image_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'))
    image_url = db.Column(db.Text) 