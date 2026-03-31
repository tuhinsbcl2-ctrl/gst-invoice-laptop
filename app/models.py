"""
SQLAlchemy models for the GST Billing Application.
"""
from datetime import datetime
from app import db

# ---------------------------------------------------------------------------
# Helper: compute current stock for a product from the InventoryLedger
# ---------------------------------------------------------------------------

def get_product_stock(product_id):
    """Return the net available stock for a product (sum of qty_in - qty_out)."""
    from sqlalchemy import func
    result = db.session.query(
        func.coalesce(func.sum(InventoryLedger.qty_in), 0).label('total_in'),
        func.coalesce(func.sum(InventoryLedger.qty_out), 0).label('total_out'),
    ).filter(InventoryLedger.product_id == product_id).one()
    return float(result.total_in) - float(result.total_out)


class AccountHead(db.Model):
    __tablename__ = 'account_heads'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)
    # account_type values: 'Direct Income', 'Indirect Income', 'Direct Expense',
    # 'Indirect Expense', 'Fixed Assets', 'Current Assets', 'Current Liabilities',
    # 'Capital Account', 'Bank Account', 'Cash Account'
    parent_id = db.Column(db.Integer, db.ForeignKey('account_heads.id'), nullable=True)
    description = db.Column(db.String(300))
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship('AccountHead', remote_side=[id], backref='children')


class Supplier(db.Model):
    __tablename__ = 'suppliers'
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
    # Google Drive backup folder (local path inside GDrive sync folder)
    gdrive_backup_folder = db.Column(db.String(500))


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
    # Ship-to details (when different from bill-to)
    ship_to_same = db.Column(db.Boolean, default=True)
    ship_to_name = db.Column(db.String(200))
    ship_to_address = db.Column(db.Text)
    ship_to_state = db.Column(db.String(50))
    ship_to_gstin = db.Column(db.String(20))
    # e-Way bill / Way Bill number
    way_bill_no = db.Column(db.String(50))
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


class PurchaseVoucher(db.Model):
    __tablename__ = 'purchase_vouchers'
    id = db.Column(db.Integer, primary_key=True)
    voucher_no = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    supplier_name = db.Column(db.String(200))
    supplier_gstin = db.Column(db.String(20))
    supplier_address = db.Column(db.Text)
    voucher_type = db.Column(db.String(30), default='Regular')
    # voucher_type: 'Regular' (stock items), 'Fixed Asset', 'Expense'
    account_head_id = db.Column(db.Integer, db.ForeignKey('account_heads.id'), nullable=True)
    invoice_no = db.Column(db.String(50))
    payment_mode = db.Column(db.String(20), default='Bank')
    payment_status = db.Column(db.String(20), default='Unpaid')
    is_igst = db.Column(db.Boolean, default=False)
    subtotal = db.Column(db.Float, default=0.0)
    cgst_total = db.Column(db.Float, default=0.0)
    sgst_total = db.Column(db.Float, default=0.0)
    igst_total = db.Column(db.Float, default=0.0)
    round_off = db.Column(db.Float, default=0.0)
    grand_total = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = db.relationship('Supplier', backref='purchase_vouchers')
    account_head = db.relationship('AccountHead', foreign_keys=[account_head_id])
    items = db.relationship('PurchaseVoucherItem', backref='voucher', lazy=True,
                            cascade='all, delete-orphan')


class PurchaseVoucherItem(db.Model):
    __tablename__ = 'purchase_voucher_items'
    id = db.Column(db.Integer, primary_key=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey('purchase_vouchers.id'), nullable=False)
    sl_no = db.Column(db.Integer)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    description = db.Column(db.String(300))
    hsn_code = db.Column(db.String(20))
    gst_rate = db.Column(db.Float, default=5.0)
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default='Pcs')
    unit_price = db.Column(db.Float, default=0.0)
    amount = db.Column(db.Float, default=0.0)
    cgst_amount = db.Column(db.Float, default=0.0)
    sgst_amount = db.Column(db.Float, default=0.0)
    igst_amount = db.Column(db.Float, default=0.0)
    account_head_id = db.Column(db.Integer, db.ForeignKey('account_heads.id'), nullable=True)


class BankTransaction(db.Model):
    __tablename__ = 'bank_transactions'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(500))
    reference_no = db.Column(db.String(100))
    debit = db.Column(db.Float, default=0.0)
    credit = db.Column(db.Float, default=0.0)
    balance = db.Column(db.Float, default=0.0)
    bank_name = db.Column(db.String(100))
    category = db.Column(db.String(100))
    account_head_id = db.Column(db.Integer, db.ForeignKey('account_heads.id'), nullable=True)
    is_reconciled = db.Column(db.Boolean, default=False)
    linked_invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)
    linked_purchase_id = db.Column(db.Integer, db.ForeignKey('purchase_vouchers.id'), nullable=True)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)

    account_head = db.relationship('AccountHead', foreign_keys=[account_head_id])
    linked_invoice = db.relationship('Invoice', foreign_keys=[linked_invoice_id])
    linked_purchase = db.relationship('PurchaseVoucher', foreign_keys=[linked_purchase_id])


class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(300))
    amount = db.Column(db.Float, default=0.0)
    mode = db.Column(db.String(20), default='Cash')  # Cash/Bank
    bank_name = db.Column(db.String(100))
    category = db.Column(db.String(100))
    account_head_id = db.Column(db.Integer, db.ForeignKey('account_heads.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    account_head = db.relationship('AccountHead', foreign_keys=[account_head_id])


class InvoiceSequence(db.Model):
    __tablename__ = 'invoice_sequence'
    id = db.Column(db.Integer, primary_key=True)
    prefix = db.Column(db.String(10), nullable=False)
    financial_year = db.Column(db.String(10), nullable=False)
    last_serial = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('prefix', 'financial_year'),)


# ---------------------------------------------------------------------------
# Inventory Ledger – records each stock movement
# ---------------------------------------------------------------------------

class InventoryLedger(db.Model):
    __tablename__ = 'inventory_ledger'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    qty_in = db.Column(db.Float, default=0.0)
    qty_out = db.Column(db.Float, default=0.0)
    # source_type: 'purchase' | 'sale' | 'purchase_return' | 'sales_return' | 'adjustment'
    source_type = db.Column(db.String(30), nullable=False)
    source_id = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', backref='ledger_entries')


# ---------------------------------------------------------------------------
# Purchase Return
# ---------------------------------------------------------------------------

class PurchaseReturn(db.Model):
    __tablename__ = 'purchase_returns'
    id = db.Column(db.Integer, primary_key=True)
    return_no = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False)
    original_voucher_id = db.Column(db.Integer, db.ForeignKey('purchase_vouchers.id'), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    supplier_name = db.Column(db.String(200))
    supplier_gstin = db.Column(db.String(20))
    reason = db.Column(db.String(300))
    is_igst = db.Column(db.Boolean, default=False)
    subtotal = db.Column(db.Float, default=0.0)
    cgst_total = db.Column(db.Float, default=0.0)
    sgst_total = db.Column(db.Float, default=0.0)
    igst_total = db.Column(db.Float, default=0.0)
    grand_total = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    original_voucher = db.relationship('PurchaseVoucher', foreign_keys=[original_voucher_id])
    supplier = db.relationship('Supplier', foreign_keys=[supplier_id])
    items = db.relationship('PurchaseReturnItem', backref='purchase_return', lazy=True,
                            cascade='all, delete-orphan')


class PurchaseReturnItem(db.Model):
    __tablename__ = 'purchase_return_items'
    id = db.Column(db.Integer, primary_key=True)
    return_id = db.Column(db.Integer, db.ForeignKey('purchase_returns.id'), nullable=False)
    sl_no = db.Column(db.Integer)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    description = db.Column(db.String(300))
    hsn_code = db.Column(db.String(20))
    gst_rate = db.Column(db.Float, default=5.0)
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default='Pcs')
    unit_price = db.Column(db.Float, default=0.0)
    amount = db.Column(db.Float, default=0.0)
    cgst_amount = db.Column(db.Float, default=0.0)
    sgst_amount = db.Column(db.Float, default=0.0)
    igst_amount = db.Column(db.Float, default=0.0)

    product = db.relationship('Product', foreign_keys=[product_id])


# ---------------------------------------------------------------------------
# Sales Return
# ---------------------------------------------------------------------------

class SalesReturn(db.Model):
    __tablename__ = 'sales_returns'
    id = db.Column(db.Integer, primary_key=True)
    return_no = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False)
    original_invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    customer_name = db.Column(db.String(200))
    customer_gstin = db.Column(db.String(20))
    reason = db.Column(db.String(300))
    is_igst = db.Column(db.Boolean, default=False)
    subtotal = db.Column(db.Float, default=0.0)
    cgst_total = db.Column(db.Float, default=0.0)
    sgst_total = db.Column(db.Float, default=0.0)
    igst_total = db.Column(db.Float, default=0.0)
    grand_total = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    original_invoice = db.relationship('Invoice', foreign_keys=[original_invoice_id])
    customer = db.relationship('Customer', foreign_keys=[customer_id])
    items = db.relationship('SalesReturnItem', backref='sales_return', lazy=True,
                            cascade='all, delete-orphan')


class SalesReturnItem(db.Model):
    __tablename__ = 'sales_return_items'
    id = db.Column(db.Integer, primary_key=True)
    return_id = db.Column(db.Integer, db.ForeignKey('sales_returns.id'), nullable=False)
    sl_no = db.Column(db.Integer)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    description = db.Column(db.String(300))
    hsn_code = db.Column(db.String(20))
    gst_rate = db.Column(db.Float, default=5.0)
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default='Pcs')
    unit_price = db.Column(db.Float, default=0.0)
    amount = db.Column(db.Float, default=0.0)
    cgst_amount = db.Column(db.Float, default=0.0)
    sgst_amount = db.Column(db.Float, default=0.0)
    igst_amount = db.Column(db.Float, default=0.0)

    product = db.relationship('Product', foreign_keys=[product_id])
