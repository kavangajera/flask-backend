from flask import Blueprint, request, jsonify
from middlewares.auth import token_required
from extensions import db
from models.device import DeviceTransaction
from datetime import datetime


device_transaction_bp = Blueprint('device_transaction', __name__)


@device_transaction_bp.route('/search-device', methods=['POST'])
@token_required(roles=['admin', 'customer'])  # Adjust roles as needed
def search_device():
    data = request.get_json()
    search_term = data.get('search_term')
    
    if not search_term:
        return jsonify({'success': False, 'message': 'Search term required'}), 400

    try:
        # Search by either device_srno or sku_id
        transactions = DeviceTransaction.query.filter(
            (DeviceTransaction.device_srno == search_term) | 
            (DeviceTransaction.sku_id == search_term)
        ).order_by(DeviceTransaction.create_date).all()

        if not transactions:
            return jsonify({'success': False, 'message': 'No transactions found'}), 404

        # Analyze transactions
        in_trans = next((t for t in transactions if t.in_out == 1), None)
        out_trans = next((t for t in transactions if t.in_out == 2), None)
        return_trans = next((t for t in transactions if t.in_out == 3), None)

        response = {
            'device_srno': transactions[0].device_srno,
            'sku_id': transactions[0].sku_id,
            'device_name': transactions[0].device_name
        }

        if return_trans:
            response['status'] = 'RETURN'
            response['message'] = 'Return transaction'
            response['return_details'] = {
                'date': return_trans.create_date.isoformat(),
                'remarks': return_trans.remarks
            }
        elif in_trans and out_trans:
            profit = float(out_trans.price) - float(in_trans.price)
            response['status'] = 'SOLD'
            response['profit'] = profit
            response['in_price'] = float(in_trans.price)
            response['out_price'] = float(out_trans.price)
            response['in_date'] = in_trans.create_date.isoformat()
            response['out_date'] = out_trans.create_date.isoformat()
        elif in_trans and not out_trans:
            response['status'] = 'IN_STOCK'
            response['message'] = 'No OUT transaction found'
            response['in_price'] = float(in_trans.price)
            response['in_date'] = in_trans.create_date.isoformat()
        elif out_trans and not in_trans:
            response['status'] = 'SOLD_WITHOUT_IN'
            response['message'] = 'No IN transaction found'
            response['out_price'] = float(out_trans.price)
            response['out_date'] = out_trans.create_date.isoformat()
        else:
            response['status'] = 'UNKNOWN'
            response['message'] = 'Unexpected transaction combination'

        return jsonify({'success': True, 'data': response})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    

    

@device_transaction_bp.route('/get-all-device-transactions', methods=['GET'])
def get_all_device_transactions():
    try:
        device_srno = request.args.get('device_srno')
        
        if device_srno:
            # Search for specific device
            transactions = DeviceTransaction.query.filter(
                DeviceTransaction.device_srno == device_srno
            ).order_by(DeviceTransaction.create_date.desc()).all()
        else:
            # Get all devices if no srno specified
            transactions = DeviceTransaction.query.order_by(
                DeviceTransaction.create_date.desc()
            ).all()

        if not transactions:
            return jsonify({
                'success': True,
                'data': [],
                'message': 'No transactions found' if device_srno else 'No devices in database'
            })

        # Serialize the transactions
        data = []
        for t in transactions:
            data.append({
                'id': t.auto_id,
                'device_srno': t.device_srno,
                'device_name': t.device_name,
                'sku_id': t.sku_id,
                'order_id': t.order_id,
                'in_out': t.in_out,
                'create_date': t.create_date.isoformat() if t.create_date else None,
                'price': float(t.price) if t.price else None,
                'remarks': t.remarks
            })

        return jsonify({
            'success': True,
            'data': data,
            'message': f'Found {len(data)} transactions'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@device_transaction_bp.route('/add-device', methods=['POST'])
def add_device():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('device_srno') or not data.get('device_name'):
            return jsonify({'success': False, 'message': 'Device SR No and Name are required'}), 400
        
        # Create new device transaction
        new_device = DeviceTransaction(
            device_srno=data['device_srno'],
            device_name=data['device_name'],
            sku_id=data.get('sku_id', ''),
            order_id=data.get('order_id', ''),
            in_out=int(data.get('in_out', 1)),
            price=float(data['price']) if 'price' in data else None,
            remarks=data.get('remarks', ''),
            create_date=datetime.now()
        )
        
        db.session.add(new_device)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Device added successfully',
            'data': {
                'device_srno': new_device.device_srno,
                'device_name': new_device.device_name
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
