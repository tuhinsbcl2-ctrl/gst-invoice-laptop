"""
SQLAlchemy models for the GST Billing Application.
"""
from datetime import datetime
from app import db


class CompanySettings(db.Model):
    __tablename__ = 'company_settings'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    gstin = db.Column(db.String(20))
    pan = db.Column(db.String(15))
    udyam = db.Column(db.String(30))
    state_name = db.Column(db.String(50))
    state_code = db.Column(db.String(5))
    bank_name = db.Column(db.String(100))
    bank_account = db.Column(db.String(30))
    bank_ifsc = db.Column(db.String(15))
    bank_branch = db.Column(db.String(100))
    invoice_prefix = db.Column(db.String(10), default='NE')
    logo_path = db.Column(db.String(200))


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    gstin = db.Column(db.String(20))
    pan = db.Column(db.String(15))
    state_name = db.Column(db.String(50))
    state_code = db.Column(db.String(5))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoices = db.relationship('Invoice', backref='buyer', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'gstin': self.gstin,
            'pan': self.pan,
            'state_name': self.state_name,
            'state_code': self.state_code,
            'phone': self.phone,
            'email': self.email,
        }


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    catalog_no = db.Column(db.String(50))
    name = db.Column(db.String(200), nullable=False)
    hsn_code = db.Column(db.String(20))
    default_gst_rate = db.Column(db.Float, default=5.0)
    default_unit_price = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default='Pcs')
    stock_quantity = db.Column(db.Float, default=0.0)
    low_stock_threshold = db.Column(db.Float, default=10.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'catalog_no': self.catalog_no,
            'name': self.name,
            'hsn_code': self.hsn_code,
            'default_gst_rate': self.default_gst_rate,
            'default_unit_price': self.default_unit_price,
            'unit': self.unit,
            'stock_quantity': self.stock_quantity,
            'low_stock_threshold': self.low_stock_threshold,
        }


class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False)
    challan_no = db.Column(db.String(50))
    challan_date = db.Column(db.Date)
    buyer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    buyer_name = db.Column(db.String(200))
    buyer_address = db.Column(db.Text)
    buyer_gstin = db.Column(db.String(20))
    buyer_state_name = db.Column(db.String(50))
    buyer_state_code = db.Column(db.String(5))
    buyer_order_no = db.Column(db.String(100))
    buyer_order_date = db.Column(db.Date)
    reference_no_date = db.Column(db.String(100))
    other_references = db.Column(db.String(200))
    other_document_no = db.Column(db.String(100))
    dispatched_through = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    bill_of_lading = db.Column(db.String(100))
    motor_vehicle_no = db.Column(db.String(50))
    terms_of_delivery = db.Column(db.String(100))
    payment_mode = db.Column(db.String(20), default='Bank')  # Cash/Bank
    payment_status = db.Column(db.String(20), default='Unpaid')  # Paid/Unpaid/Partial
    place_of_supply = db.Column(db.String(50))
    place_of_supply_code = db.Column(db.String(5))
    is_igst = db.Column(db.Boolean, default=False)
    subtotal = db.Column(db.Float, default=0.0)
    cgst_total = db.Column(db.Float, default=0.0)
    sgst_total = db.Column(db.Float, default=0.0)
    igst_total = db.Column(db.Float, default=0.0)
    round_off = db.Column(db.Float, default=0.0)
    grand_total = db.Column(db.Float, default=0.0)
    amount_in_words = db.Column(db.String(500))
    tax_amount_in_words = db.Column(db.String(500))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('InvoiceItem', backref='invoice', lazy=True,
                            cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_no': self.invoice_no,
            'date': self.date.strftime('%d-%b-%y') if self.date else '',
            'challan_no': self.challan_no,
            'challan_date': self.challan_date.strftime('%d-%b-%y') if self.challan_date else '',
            'buyer_name': self.buyer_name,
            'buyer_address': self.buyer_address,
            'buyer_gstin': self.buyer_gstin,
            'buyer_state_name': self.buyer_state_name,
            'buyer_state_code': self.buyer_state_code,
            'buyer_order_no': self.buyer_order_no,
            'buyer_order_date': self.buyer_order_date.strftime('%d-%b-%y') if self.buyer_order_date else '',
            'reference_no_date': self.reference_no_date,
            'other_references': self.other_references,
            'other_document_no': self.other_document_no,
            'dispatched_through': self.dispatched_through,
            'destination': self.destination,
            'bill_of_lading': self.bill_of_lading,
            'motor_vehicle_no': self.motor_vehicle_no,
            'terms_of_delivery': self.terms_of_delivery,
            'payment_mode': self.payment_mode,
            'payment_status': self.payment_status,
            'place_of_supply': self.place_of_supply,
            'place_of_supply_code': self.place_of_supply_code,
            'is_igst': self.is_igst,
            'subtotal': self.subtotal,
            'cgst_total': self.cgst_total,
            'sgst_total': self.sgst_total,
            'igst_total': self.igst_total,
            'round_off': self.round_off,
            'grand_total': self.grand_total,
            'amount_in_words': self.amount_in_words,
            'tax_amount_in_words': self.tax_amount_in_words,
            'notes': self.notes,
            'items': [item.to_dict() for item in self.items],
        }


class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    sl_no = db.Column(db.Integer)
    catalog_no = db.Column(db.String(50))
    description = db.Column(db.String(300))
    hsn_code = db.Column(db.String(20))
    gst_rate = db.Column(db.Float, default=5.0)
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default='Pcs')
    unit_price = db.Column(db.Float, default=0.0)
    amount = db.Column(db.Float, default=0.0)
    cgst_rate = db.Column(db.Float, default=0.0)
    cgst_amount = db.Column(db.Float, default=0.0)
    sgst_rate = db.Column(db.Float, default=0.0)
    sgst_amount = db.Column(db.Float, default=0.0)
    igst_rate = db.Column(db.Float, default=0.0)
    igst_amount = db.Column(db.Float, default=0.0)
    # Challan-specific fields
    lot_no = db.Column(db.String(50))
    mfg_date = db.Column(db.String(20))
    exp_date = db.Column(db.String(20))

    def to_dict(self):
        return {
            'id': self.id,
            'sl_no': self.sl_no,
            'catalog_no': self.catalog_no,
            'description': self.description,
            'hsn_code': self.hsn_code,
            'gst_rate': self.gst_rate,
            'quantity': self.quantity,
            'unit': self.unit,
            'unit_price': self.unit_price,
            'amount': self.amount,
            'cgst_rate': self.cgst_rate,
            'cgst_amount': self.cgst_amount,
            'sgst_rate': self.sgst_rate,
            'sgst_amount': self.sgst_amount,
            'igst_rate': self.igst_rate,
            'igst_amount': self.igst_amount,
            'lot_no': self.lot_no,
            'mfg_date': self.mfg_date,
            'exp_date': self.exp_date,
        }


class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(300))
    amount = db.Column(db.Float, default=0.0)
    mode = db.Column(db.String(20), default='Cash')  # Cash/Bank
    bank_name = db.Column(db.String(100))
    category = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class InvoiceSequence(db.Model):
    __tablename__ = 'invoice_sequence'
    id = db.Column(db.Integer, primary_key=True)
    prefix = db.Column(db.String(10), nullable=False)
    financial_year = db.Column(db.String(10), nullable=False)
    last_serial = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('prefix', 'financial_year'),)
