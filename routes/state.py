from flask import Blueprint, jsonify
from models.state import State

state_bp = Blueprint('state', __name__)

@state_bp.route('/states', methods=['GET'])
def get_states():
    """Get all states for dropdown"""
    states = State.query.order_by(State.name).all()
    return jsonify({
        'success': True,
        'states': [state.to_dict() for state in states]
    })