from extensions import db
from datetime import datetime
from zoneinfo import ZoneInfo
class StockNotification(db.Model):

    __tablename__ = 'stock_notifications'

    id = db.Column(db.Integer, primary_key=True)
    color_id = db.Column(db.Integer, db.ForeignKey('product_colors.color_id'), nullable=False)
    product_name = db.Column(db.String(255))
    notified_at = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo('Asia/Kolkata')))


    color = db.relationship('ProductColor', backref=db.backref('notifications', lazy=True))
