from flask import Blueprint, current_app, request, jsonify
from middlewares.auth import token_required
from extensions import db
from models.customer import Customer
import requests


profile_bp = Blueprint('profile',__name__)

@profile_bp.route('/profile-info',methods=['GET'])
@token_required(roles=['customer','admin'])
def get_profile_info():
    current_user = request.current_user
    profile = Customer.query.filter_by(customer_id=current_user.customer_id).first()
    return jsonify({
        'success' : True,
        'profile-info': profile.get_dict()
    })