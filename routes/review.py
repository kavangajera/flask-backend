from flask import Blueprint, request, jsonify
from extensions import db
from models.review import Review
from models.product import Product
from models.order import Order, OrderItem
from middlewares.auth import token_required

reviews_bp = Blueprint('reviews', __name__)

@reviews_bp.route('/review', methods=['POST'])
@token_required(roles=['customer'])

def post_review():
    """
    Create a new review for a product
    Verifies that user has purchased the product before allowing review
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    required_fields = ['product_id', 'rating', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Validate rating is between 1 and 5
    if not 1 <= data['rating'] <= 5:
        return jsonify({"error": "Rating must be between 1 and 5"}), 400
    
    product_id = data['product_id']
    customer_id = request.current_user.customer_id
    
    # Check if product exists
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    # Check if user has already reviewed this product
    existing_review = Review.query.filter_by(
        product_id=product_id, 
        customer_id=customer_id
    ).first()
    
    if existing_review:
        return jsonify({"error": "You have already reviewed this product"}), 400
    
    # Check if user has purchased this product
    # Find orders containing this product for this customer
    orders = Order.query.filter_by(customer_id=customer_id).all()
    order_ids = [order.order_id for order in orders]
    
    # Check if any order contains this product
    purchased = False
    if order_ids:
        purchased_items = OrderItem.query.filter(
            OrderItem.order_id.in_(order_ids),
            OrderItem.product_id == product_id
        ).first()
        
        if purchased_items:
            purchased = True
    
    if not purchased:
        return jsonify({
            "error": "You can only review products you have purchased"
        }), 403
    
    # Create new review
    new_review = Review(
        product_id=product_id,
        customer_id=customer_id,
        rating=data['rating'],
        description=data['description']
    )
    
    try:
        db.session.add(new_review)
        db.session.commit()
        
        # Update product rating
        product.update_rating()
        
        return jsonify({
            "message": "Review submitted successfully",
            "review": new_review.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@reviews_bp.route('/reviews', methods=['GET'])
def get_all_reviews():
    """
    Get all reviews as a simple array
    """
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    
    return jsonify([review.to_dict() for review in reviews]), 200


@reviews_bp.route('/reviews/customer/<int:customer_id>', methods=['GET'])
def get_reviews_by_customer(customer_id):
    """
    Get all reviews by a specific customer as a simple array
    """
    reviews = Review.query.filter_by(customer_id=customer_id).order_by(
        Review.created_at.desc()
    ).all()
    
    return jsonify([review.to_dict() for review in reviews]), 200


@reviews_bp.route('/reviews/product/<int:product_id>', methods=['GET'])
def get_reviews_by_product(product_id):
    """
    Get all reviews for a specific product as a simple array
    with product rating data
    """
    # First check if product exists
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    reviews = Review.query.filter_by(product_id=product_id).order_by(
        Review.created_at.desc()
    ).all()
    
    return jsonify({
        "reviews": [review.to_dict() for review in reviews],
        "average_rating": product.rating,
        "total_reviews": product.raters
    }), 200


@reviews_bp.route('/reviews/<int:review_id>', methods=['GET'])
def get_review_by_id(review_id):
    """
    Get a specific review by ID
    """
    review = Review.query.get(review_id)
    
    if not review:
        return jsonify({"error": "Review not found"}), 404
    
    return jsonify(review.to_dict()), 200


@reviews_bp.route('/reviews/<int:review_id>', methods=['PUT'])
@token_required(roles=['customer'])
def update_review(review_id):
    """
    Update a review (only if current user owns it)
    """
    review = Review.query.get(review_id)
    
    if not review:
        return jsonify({"error": "Review not found"}), 404
    
    # Verify the review belongs to the current user
    if review.customer_id != request.current_user.customer_id:
        return jsonify({"error": "You cannot modify this review"}), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Update fields if provided
    if 'rating' in data:
        if not 1 <= data['rating'] <= 5:
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
        review.rating = data['rating']
    
    if 'description' in data:
        review.description = data['description']
    
    try:
        db.session.commit()
        
        # Update product rating
        product = Product.query.get(review.product_id)
        product.update_rating()
        
        return jsonify({
            "message": "Review updated successfully",
            "review": review.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@reviews_bp.route('/reviews/<int:review_id>', methods=['DELETE'])
@token_required(roles=['customer'])
def delete_review(review_id):
    """
    Delete a review (only if current user owns it or is admin)
    """
    review = Review.query.get(review_id)
    
    if not review:
        return jsonify({"error": "Review not found"}), 404
    
    # Verify the review belongs to the current user or user is admin
    if review.customer_id !=  request.current_user.customer_id and not request.current_user.is_admin():
        return jsonify({"error": "You cannot delete this review"}), 403
    
    product_id = review.product_id
    
    try:
        db.session.delete(review)
        db.session.commit()
        
        # Update product rating
        product = Product.query.get(product_id)
        product.update_rating()
        
        return jsonify({"message": "Review deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@reviews_bp.route('/reviews/customer/me', methods=['GET'])
@token_required(roles=['customer'])
def get_my_reviews():
    """
    Get all reviews by the currently logged in customer as a simple array
    """
    reviews = Review.query.filter_by(customer_id = request.current_user.customer_id).order_by(
        Review.created_at.desc()
    ).all()
    
    return jsonify([review.to_dict() for review in reviews]), 200


@reviews_bp.route('/reviews/check/<int:product_id>', methods=['GET'])
@token_required(roles=['customer'])
def check_review_eligibility(product_id):
    """
    Check if the current user can review a specific product
    Returns: 
    - has_purchased: Whether user has purchased the product
    - has_reviewed: Whether user has already reviewed the product
    """
    customer_id = request.current_user.customer_id
    
    # Check if product exists
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    # Check if user has already reviewed this product
    existing_review = Review.query.filter_by(
        product_id=product_id, 
        customer_id=customer_id
    ).first()
    
    has_reviewed = existing_review is not None
    
    # Check if user has purchased this product
    orders = Order.query.filter_by(customer_id=customer_id).all()
    order_ids = [order.order_id for order in orders]
    
    has_purchased = False
    if order_ids:
        purchased_items = OrderItem.query.filter(
            OrderItem.order_id.in_(order_ids),
            OrderItem.product_id == product_id
        ).first()
        
        if purchased_items:
            has_purchased = True
    
    return jsonify({
        "product_id": product_id,
        "has_purchased": has_purchased,
        "has_reviewed": has_reviewed,
        "can_review": has_purchased and not has_reviewed,
        "existing_review": existing_review.to_dict() if existing_review else None
    }), 200