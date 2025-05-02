from extensions import db

class DeviceTransaction(db.Model):
    __tablename__ = 'device_transaction'

    auto_id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Auto_ID
    device_srno = db.Column(db.String(100), nullable=False)                # Device_SRNO
    device_name = db.Column(db.String(100), nullable=False)                # Device_Name
    sku_id = db.Column(db.String(100), nullable=False)                     # SKU_ID
    order_id = db.Column(db.String(50), nullable=False )        # Order_ID
    in_out = db.Column(db.Integer, nullable=False)                         # IN_Out (1=IN, 2=OUT, 3=RETURN)
    create_date = db.Column(db.Date, nullable=False)                       # Create_date
    price = db.Column(db.Numeric(10, 2), nullable=True)                    # Price
    remarks = db.Column(db.String(255), nullable=True)                     # Remarks

    def __repr__(self):
        return f"<DeviceTransaction {self.device_srno} - {self.order_id}>"
