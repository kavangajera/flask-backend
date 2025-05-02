from models.product import ProductColor, Product
from models.stock_notification import StockNotification
from extensions import db
import os, smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'sodagaramaan786@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'gsin qzbq xuqw qihp')
ALERT_RECEIVER = os.getenv('ALERT_RECEIVER', 'sodagaramaanwork@gmail.com')

def send_low_stock_email(products, subject):
    try:
        # Preparing the subject and body for the email
        body = "The following products need attention:\n\n"
        for product in products:
            body += (
                f"Product Name: {product['name']}\n"
                f"Color: {product['color_name']}\n"
                f"Current Stock: {product['stock_quantity']}\n"
                f"Threshold: {product['threshold']}\n"
                f"Price: ₹{product['price']}\n"
                f"Product ID: {product['product_id']}\n\n"
            )

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = ALERT_RECEIVER

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        print(f" Email sent for {subject.lower()}.")
        return True

    except Exception as e:
        print(f" Failed to send email: {e}")
        return False

def check_and_notify():
    from app import app

    with app.app_context():
        print(f"🔄 Checking stock at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Query for stock status
        low_stock_colors = ProductColor.query.filter(
            (ProductColor.stock_quantity <= ProductColor.threshold) & (ProductColor.stock_quantity > 0)
        ).all()
        out_of_stock_colors = ProductColor.query.filter(ProductColor.stock_quantity == 0).all()

        low_stock_to_notify = []
        out_of_stock_to_notify = []

        # Process low stock items
        for color in low_stock_colors:
            product = Product.query.filter_by(product_id=color.product_id).first()
            # Check for existing notification within 2 days
            existing_notification = StockNotification.query.filter(
                StockNotification.color_id == color.color_id,
                StockNotification.notified_at >= datetime.now() - timedelta(days=2)
            ).first()

            if not existing_notification:
                low_stock_to_notify.append({
                    "name": product.name,
                    "color_name": color.name,
                    "stock_quantity": color.stock_quantity,
                    "threshold": color.threshold,
                    "price": color.price,
                    "product_id": color.product_id,
                    "color_id": color.color_id  # Added this for saving later
                })

        # Process out of stock items (same logic)
        for color in out_of_stock_colors:
            product = Product.query.filter_by(product_id=color.product_id).first()
            existing_notification = StockNotification.query.filter(
                StockNotification.color_id == color.color_id,
                StockNotification.notified_at >= datetime.now() - timedelta(days=2)
            ).first()

            if not existing_notification:
                out_of_stock_to_notify.append({
                    "name": product.name,
                    "color_name": color.name,
                    "stock_quantity": color.stock_quantity,
                    "threshold": color.threshold,
                    "price": color.price,
                    "product_id": color.product_id,
                    "color_id": color.color_id  # Added this for saving later
                })

        # Send notifications and save records
        if low_stock_to_notify:
            if send_low_stock_email(low_stock_to_notify, "Low Stock Alert"):
                for product in low_stock_to_notify:
                    notification = StockNotification(
                        color_id=product['color_id'],  # Use the color_id from the product dict
                        product_name=product['name'],
                        notified_at=datetime.now()
                    )
                    db.session.add(notification)
                db.session.commit()

        if out_of_stock_to_notify:
            if send_low_stock_email(out_of_stock_to_notify, "Out of Stock Alert"):
                for product in out_of_stock_to_notify:
                    notification = StockNotification(
                        color_id=product['color_id'],  # Use the color_id from the product dict
                        product_name=product['name'],
                        notified_at=datetime.now()
                    )
                    db.session.add(notification)
                db.session.commit()

        # Cleanup old notifications
        StockNotification.query.filter(
            StockNotification.notified_at < datetime.now() - timedelta(days=2)
        ).delete()
        db.session.commit()
