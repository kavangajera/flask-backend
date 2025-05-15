from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from models.order import Order, OrderItem, OrderDetail
from models.customer import Customer
from models.offline_customer import OfflineCustomer
from models.product import Product, ProductColor
from models.address import Address
from extensions import db

admin_bp = Blueprint('admin_dashboard', __name__)

@admin_bp.route('/dashboard/summary')
def dashboard_summary():
    """Get today's, weekly, monthly revenue and counts"""
    # Calculate dates
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Queries
    today_rev = db.session.query(func.sum(Order.total_amount)).filter(
        func.date(Order.created_at) == today
    ).scalar() or 0
    
    week_rev = db.session.query(func.sum(Order.total_amount)).filter(
        func.date(Order.created_at) >= week_start
    ).scalar() or 0
    
    month_rev = db.session.query(func.sum(Order.total_amount)).filter(
        func.date(Order.created_at) >= month_start
    ).scalar() or 0
    
    pending_orders = db.session.query(func.count(Order.order_id)).filter(
        Order.delivery_status == 'pending'
    ).scalar() or 0
    
    return jsonify({
        'today_revenue': float(today_rev),
        'week_revenue': float(week_rev),
        'month_revenue': float(month_rev),
        'pending_orders': pending_orders,
        'online_offline_split': get_channel_split()
    })

def get_channel_split():
    """Get online vs offline sales percentage"""
    total = db.session.query(func.sum(Order.total_amount)).scalar() or 1
    online = db.session.query(func.sum(Order.total_amount)).filter(
        Order.channel == 'online'
    ).scalar() or 0
    
    offline = total - online
    return {
        'online': {'amount': float(online), 'percent': round((online/total)*100, 2)},
        'offline': {'amount': float(offline), 'percent': round((offline/total)*100, 2)}
    }

@admin_bp.route('/dashboard/best-sellers')
def best_sellers():
    """Get top 5 best selling products"""
    result = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_quantity'),
        func.sum(OrderItem.total_price).label('total_revenue')
    ).join(OrderItem, Product.product_id == OrderItem.product_id
    ).group_by(Product.name
    ).order_by(func.sum(OrderItem.quantity).desc()
    ).limit(5).all()
    
    return jsonify([{
        'product': r[0],
        'units_sold': r[1],
        'revenue': float(r[2])
    } for r in result])

@admin_bp.route('/dashboard/customers')
def customer_insights():
    """Get customer insights with order history"""
    customers = db.session.query(
        Customer,
        func.count(Order.order_id),
        func.sum(Order.total_amount)
    ).outerjoin(Order, Customer.customer_id == Order.customer_id
    ).group_by(Customer.customer_id).all()
    
    return jsonify([{
        'customer_id': c.customer_id,
        'name': c.name,
        'mobile': c.mobile,
        'email': c.email,
        'total_orders': orders or 0,
        'total_spent': float(spent) if spent else 0,
        'last_order': get_last_order_date(c.customer_id)
    } for c, orders, spent in customers])

def get_last_order_date(customer_id):
    last_order = db.session.query(Order.created_at).filter(
        Order.customer_id == customer_id
    ).order_by(Order.created_at.desc()).first()
    return last_order[0].strftime('%Y-%m-%d') if last_order else None

@admin_bp.route('/dashboard/orders')
def order_management():
    """Get orders with date filtering"""
    # Get filter params
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')
    
    # Base query
    query = db.session.query(
        Order,
        func.coalesce(Customer.name, OfflineCustomer.name).label('customer_name')
    ).outerjoin(Customer, Order.customer_id == Customer.customer_id
    ).outerjoin(OfflineCustomer, Order.offline_customer_id == OfflineCustomer.customer_id)
    
    # Apply filters
    if start_date and end_date:
        query = query.filter(and_(
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date
        ))
    elif start_date:
        query = query.filter(func.date(Order.created_at) >= start_date)
    elif end_date:
        query = query.filter(func.date(Order.created_at) <= end_date)
    
    if status:
        query = query.filter(Order.delivery_status == status)
    
    # Get results
    orders = query.order_by(Order.created_at.desc()).all()
    
    return jsonify([{
        'order_id': o.order_id,
        'date': o.created_at.strftime('%Y-%m-%d'),
        'customer': customer_name,
        'amount': float(o.total_amount),
        'status': o.delivery_status,
        'payment_status': o.payment_status,
        'items': get_order_items(o.order_id)
    } for o, customer_name in orders])

def get_order_items(order_id):
    """Get items for a specific order"""
    items = db.session.query(
        Product.name,
        OrderItem.quantity,
        OrderItem.unit_price
    ).join(OrderItem, Product.product_id == OrderItem.product_id
    ).filter(OrderItem.order_id == order_id).all()
    
    return [{
        'product': i[0],
        'quantity': i[1],
        'price': float(i[2])
    } for i in items]