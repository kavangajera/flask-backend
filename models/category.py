from extensions import db

class Category(db.Model):
    __tablename__ = 'categories'
    
    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    # Relationships
    subcategories = db.relationship('Subcategory', backref='category', lazy=True, cascade="all, delete-orphan")
    products = db.relationship('Product', backref='main_category', lazy=True)

class Subcategory(db.Model):
    __tablename__ = 'subcategories'
    
    subcategory_id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=False)
    
    # Relationships
    products = db.relationship('Product', backref='sub_category', lazy=True)