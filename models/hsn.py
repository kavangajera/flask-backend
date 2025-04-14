from extensions import db

class HSN(db.Model):
    __tablename__ = 'hsn'
    
    hsn_id = db.Column(db.Integer, primary_key=True)
    hsn_code = db.Column(db.String(15), nullable=False)
    hsn_description = db.Column(db.String(255), nullable=False)
    gst_rate = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Relationships
    products = db.relationship('Product', backref='hsn', lazy=True, cascade="all, delete-orphan")