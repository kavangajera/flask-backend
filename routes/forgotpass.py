# routes/forgotpass.py
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from models.customer import Customer
from extensions import db
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo

forgotpass_bp = Blueprint('forgotpass', __name__)

# Dictionary to store OTPs and their expiration times (in production, use Redis)
otp_storage = {}

# Email configuration (replace with your SMTP details)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'sodagaramaan786@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'gsin qzbq xuqw qihp')

def send_otp_email(email, otp):
    """Send OTP to user's email"""
    try:
        subject = "Your Password Reset OTP"
        body = f"Your OTP for password reset is: {otp}\n\nThis OTP is valid for 10 minutes."
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = email
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@forgotpass_bp.route('/send-otp', methods=['POST'])
def send_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'message': 'Email is required'}), 400
            
        # Check if email exists in database
        customer = Customer.query.filter_by(email=email).first()
        if not customer:
            return jsonify({'message': 'Email not registered'}), 404
            
        # Generate 4-digit OTP
        otp = str(random.randint(1000, 9999))
        expiration_time = datetime.now(tz=ZoneInfo('Asia/Kolkata')) + timedelta(minutes=10)
        
        # Store OTP with expiration (in production, use Redis)
        otp_storage[email] = {
            'otp': otp,
            'expires_at': expiration_time
        }
        
        # Send OTP to email
        if not send_otp_email(email, otp):
            return jsonify({'message': 'Failed to send OTP email'}), 500
            
        return jsonify({
            'message': 'OTP sent successfully',
            'email': email
        }), 200
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@forgotpass_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        
        if not email or not otp:
            return jsonify({'message': 'Email and OTP are required'}), 400
            
        # Check if OTP exists and is not expired
        stored_otp_data = otp_storage.get(email)
        if not stored_otp_data:
            return jsonify({'message': 'OTP not found or expired'}), 404
            
        if datetime.now(tz=ZoneInfo('Asia/Kolkata')) > stored_otp_data['expires_at']:
            del otp_storage[email]
            return jsonify({'message': 'OTP expired'}), 400
            
        if stored_otp_data['otp'] != otp:
            return jsonify({'message': 'Invalid OTP'}), 400
            
        # OTP is valid
        return jsonify({
            'message': 'OTP verified successfully',
            'email': email
        }), 200
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@forgotpass_bp.route('/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        email = data.get('email')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not email or not new_password or not confirm_password:
            return jsonify({'message': 'All fields are required'}), 400
            
        if new_password != confirm_password:
            return jsonify({'message': 'Passwords do not match'}), 400
            
        if len(new_password) < 8:
            return jsonify({'message': 'Password must be at least 8 characters'}), 400
            
        # Update password in database
        customer = Customer.query.filter_by(email=email).first()
        if not customer:
            return jsonify({'message': 'User not found'}), 404
            
        customer.password = generate_password_hash(new_password)
        db.session.commit()
        
        # Clear OTP after successful password reset
        if email in otp_storage:
            del otp_storage[email]
            
        return jsonify({'message': 'Password updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500
