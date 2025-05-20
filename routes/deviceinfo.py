from flask import Blueprint, request, jsonify
from middlewares.auth import token_required
from extensions import db
from models.device import DeviceTransaction  # Adjust import based on your structure
import pandas as pd
from datetime import datetime


device_transaction_bp = Blueprint('device_transaction', __name__)

@device_transaction_bp.route('/upload-device-transaction', methods=['POST'])
@token_required(roles=['admin'])
def upload_device_transaction():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part in the request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400

    try:
        # Read file into a pandas DataFrame
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith('.xlsx'):
            try:
                df = pd.read_excel(file, engine='openpyxl')  # Explicitly specify engine
            except ImportError:
                return jsonify({
                    'success': False,
                    'message': 'Excel support requires openpyxl. Install with: pip install openpyxl'
                }), 500
        else:
            return jsonify({'success': False, 'message': 'Unsupported file format. Only CSV and Excel are allowed.'}), 400
        
        # Normalize column names
        df.columns = [col.strip() for col in df.columns]

        required_columns = [
            'Device_SRNO', 'Device_Name', 'SKU_ID', 'Order_ID', 'IN_Out', 'Create_date', 'Price', 'Remarks'
        ]
        
        # Fill missing columns with None
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        
        # Replace NaN with None
        df = df.where(pd.notnull(df), None)

        # Insert into database
        inserted_records = 0
        for index, row in df.iterrows():
            try:
                transaction = DeviceTransaction(
                    device_srno=row.get('Device_SRNO'),
                    model_name=row.get('Device_Name'),
                    sku_id=row.get('SKU_ID'),
                    order_id=row.get('Order_ID'),
                    in_out=int(row.get('IN_Out')) if row.get('IN_Out') else None,
                    create_date=pd.to_datetime(row.get('Create_date')).date() if row.get('Create_date') else None,
                    price=row.get('Price'),
                    remarks=row.get('Remarks')
                )
                db.session.add(transaction)
                inserted_records += 1
            except Exception as e:
                print(f"Error processing row {index}: {e}")
        
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{inserted_records} device transactions uploaded successfully.'
        }), 201

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    



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
            'model_name': transactions[0].model_name
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
                'model_name': t.model_name,
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

from zoneinfo import ZoneInfo

@device_transaction_bp.route('/add-device', methods=['POST'])
def add_device():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('device_srno') or not data.get('model_name'):
            return jsonify({'success': False, 'message': 'Device SR No and Name are required'}), 400
        
        # Create new device transaction
        new_device = DeviceTransaction(
            device_srno=data['device_srno'],
            model_name=data['model_name'],
            sku_id=data.get('sku_id', ''),
            order_id=data.get('order_id', ''),
            in_out=int(data.get('in_out', 1)),
            price=float(data['price']) if 'price' in data else None,
            remarks=data.get('remarks', ''),
            create_date=datetime.now(tz=ZoneInfo('Asia/Kolkata'))
        )
        
        db.session.add(new_device)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Device added successfully',
            'data': {
                'device_srno': new_device.device_srno,
                'model_name': new_device.model_name
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
