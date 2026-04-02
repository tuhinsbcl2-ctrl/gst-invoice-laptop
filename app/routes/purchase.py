"""
Purchase Voucher routes.
"""
from datetime import datetime, date
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify)
from app import db
from app.models import (PurchaseVoucher, PurchaseVoucherItem, Supplier,
                        AccountHead, InvoiceSequence, CompanySettings,
                        Product, InventoryLedger)
from app.services.invoice_numbering import get_next_invoice_number, peek_next_invoice_number
from app.services.form_helpers import parse_voucher_items

purchase_bp = Blueprint('purchase', __name__)

VOUCHER_TYPES = ['Regular', 'Fixed Asset', 'Expense']
PAYMENT_MODES = ['Cash', 'Bank', 'Credit']
PAYMENT_STATUSES = ['Unpaid', 'Paid', 'Partial']
GST_RATES = [0, 5, 12, 18, 28]
UNITS = ['Pcs', 'Nos', 'Kg', 'Ltr', 'Mtr', 'Box', 'Set', 'Pair', 'Roll', 'Sheet']


def _record_inventory(voucher, action='add'):
    """Record inventory ledger entries for a purchase voucher.

    action='add'    – create ledger entries (qty_in for Regular vouchers)
    action='remove' – delete existing ledger entries for this voucher
    """
    if action == 'remove':
        InventoryLedger.query.filter_by(
            source_type='purchase', source_id=voucher.id
        ).delete()
        return

    # Only Regular vouchers affect stock
    if voucher.voucher_type != 'Regular':
        return

    for item in voucher.items:
        pid = item.product_id
        if not pid:
            continue
        prod = Product.query.get(pid)
        if not prod:
            continue
        entry = InventoryLedger(
            date=voucher.date,
            product_id=pid,
            qty_in=item.quantity,
            qty_out=0.0,
            source_type='purchase',
            source_id=voucher.id,
            notes=f'Purchase {voucher.voucher_no}',
        )
        db.session.add(entry)
        # Also update denormalized stock_quantity on Product
        prod.stock_quantity = (prod.stock_quantity or 0.0) + item.quantity


def _parse_items(req, is_igst):
    """Thin wrapper around the shared parse_voucher_items for purchase vouchers."""
    return parse_voucher_items(req.form, is_igst, with_account_head=True)


@purchase_bp.route('/')
def list_purchases():
    vouchers = PurchaseVoucher.query.order_by(PurchaseVoucher.date.desc()).all()
    total = sum(v.grand_total for v in vouchers)
    unpaid = sum(v.grand_total for v in vouchers if v.payment_status in ('Unpaid', 'Partial'))
    return render_template('purchase/list.html', vouchers=vouchers,
                           total=total, unpaid=unpaid)


@purchase_bp.route('/create', methods=['GET', 'POST'])
def create_purchase():
    if request.method == 'POST':
        data = request.form
        voucher_date_str = data.get('date', date.today().strftime('%Y-%m-%d'))
        voucher_date = datetime.strptime(voucher_date_str, '%Y-%m-%d').date()

        voucher_no = get_next_invoice_number('PV', voucher_date)

        supplier_id = data.get('supplier_id') or None
        if supplier_id:
            supplier_id = int(supplier_id)

        account_head_id = data.get('account_head_id') or None
        if account_head_id:
            account_head_id = int(account_head_id)

        is_igst = data.get('is_igst') == 'on'

        voucher = PurchaseVoucher(
            voucher_no=voucher_no,
            date=voucher_date,
            supplier_id=supplier_id,
            supplier_name=data.get('supplier_name', ''),
            supplier_gstin=data.get('supplier_gstin', ''),
            supplier_address=data.get('supplier_address', ''),
            voucher_type=data.get('voucher_type', 'Regular'),
            account_head_id=account_head_id,
            invoice_no=data.get('invoice_no', ''),
            payment_mode=data.get('payment_mode', 'Bank'),
            payment_status=data.get('payment_status', 'Unpaid'),
            is_igst=is_igst,
            notes=data.get('notes', ''),
        )

        parsed_items, subtotal, cgst_total, sgst_total, igst_total = _parse_items(request, is_igst)

        for item_data in parsed_items:
            item = PurchaseVoucherItem(
                sl_no=item_data['sl_no'],
                product_id=item_data['product_id'],
                description=item_data['description'],
                hsn_code=item_data['hsn_code'],
                gst_rate=item_data['gst_rate'],
                quantity=item_data['quantity'],
                unit=item_data['unit'],
                unit_price=item_data['unit_price'],
                amount=item_data['amount'],
                cgst_amount=item_data['cgst_amount'],
                sgst_amount=item_data['sgst_amount'],
                igst_amount=item_data['igst_amount'],
                account_head_id=item_data['account_head_id'],
            )
            voucher.items.append(item)

        grand_total = subtotal + cgst_total + sgst_total + igst_total
        round_off = round(round(grand_total) - grand_total, 2)
        voucher.subtotal = round(subtotal, 2)
        voucher.cgst_total = round(cgst_total, 2)
        voucher.sgst_total = round(sgst_total, 2)
        voucher.igst_total = round(igst_total, 2)
        voucher.round_off = round_off
        voucher.grand_total = round(grand_total + round_off, 2)

        db.session.add(voucher)
        db.session.flush()  # get voucher.id before ledger entries

        _record_inventory(voucher, action='add')

        db.session.commit()
        flash(f'Purchase Voucher {voucher_no} created.', 'success')
        return redirect(url_for('purchase.view_purchase', vid=voucher.id))

    next_no = peek_next_invoice_number('PV')
    suppliers = Supplier.query.order_by(Supplier.name).all()
    account_heads = AccountHead.query.order_by(AccountHead.account_type, AccountHead.name).all()
    products = Product.query.order_by(Product.name).all()
    company = CompanySettings.query.first()
    company_state_code = company.state_code if company else ''
    # Pre-fill from GSTR-2B "Add to Books" link
    prefill = {
        'invoice_no': request.args.get('inv_no', ''),
        'supplier_gstin': request.args.get('supplier_gstin', ''),
        'supplier_name': request.args.get('supplier_name', ''),
        'date': request.args.get('inv_date', ''),
    }
    return render_template('purchase/form.html',
                           today=date.today().strftime('%Y-%m-%d'),
                           next_no=next_no,
                           suppliers=suppliers,
                           account_heads=account_heads,
                           products=products,
                           voucher_types=VOUCHER_TYPES,
                           payment_modes=PAYMENT_MODES,
                           payment_statuses=PAYMENT_STATUSES,
                           gst_rates=GST_RATES,
                           units=UNITS,
                           company_state_code=company_state_code,
                           prefill=prefill)


@purchase_bp.route('/<int:vid>/edit', methods=['GET', 'POST'])
def edit_purchase(vid):
    voucher = PurchaseVoucher.query.get_or_404(vid)
    if request.method == 'POST':
        data = request.form
        voucher_date_str = data.get('date', date.today().strftime('%Y-%m-%d'))
        voucher.date = datetime.strptime(voucher_date_str, '%Y-%m-%d').date()

        supplier_id = data.get('supplier_id') or None
        voucher.supplier_id = int(supplier_id) if supplier_id else None
        voucher.supplier_name = data.get('supplier_name', '')
        voucher.supplier_gstin = data.get('supplier_gstin', '')
        voucher.supplier_address = data.get('supplier_address', '')
        voucher.voucher_type = data.get('voucher_type', 'Regular')
        account_head_id = data.get('account_head_id') or None
        voucher.account_head_id = int(account_head_id) if account_head_id else None
        voucher.invoice_no = data.get('invoice_no', '')
        voucher.payment_mode = data.get('payment_mode', 'Bank')
        voucher.payment_status = data.get('payment_status', 'Unpaid')
        voucher.is_igst = data.get('is_igst') == 'on'
        voucher.notes = data.get('notes', '')

        # Remove old inventory ledger entries before rebuilding items
        _record_inventory(voucher, action='remove')

        # Reverse old stock changes
        for item in list(voucher.items):
            if item.product_id and voucher.voucher_type == 'Regular':
                prod = Product.query.get(item.product_id)
                if prod:
                    prod.stock_quantity = max(0.0, (prod.stock_quantity or 0.0) - item.quantity)
            db.session.delete(item)

        is_igst = voucher.is_igst
        parsed_items, subtotal, cgst_total, sgst_total, igst_total = _parse_items(request, is_igst)

        for item_data in parsed_items:
            item = PurchaseVoucherItem(
                voucher_id=voucher.id,
                sl_no=item_data['sl_no'],
                product_id=item_data['product_id'],
                description=item_data['description'],
                hsn_code=item_data['hsn_code'],
                gst_rate=item_data['gst_rate'],
                quantity=item_data['quantity'],
                unit=item_data['unit'],
                unit_price=item_data['unit_price'],
                amount=item_data['amount'],
                cgst_amount=item_data['cgst_amount'],
                sgst_amount=item_data['sgst_amount'],
                igst_amount=item_data['igst_amount'],
                account_head_id=item_data['account_head_id'],
            )
            db.session.add(item)

        grand_total = subtotal + cgst_total + sgst_total + igst_total
        round_off = round(round(grand_total) - grand_total, 2)
        voucher.subtotal = round(subtotal, 2)
        voucher.cgst_total = round(cgst_total, 2)
        voucher.sgst_total = round(sgst_total, 2)
        voucher.igst_total = round(igst_total, 2)
        voucher.round_off = round_off
        voucher.grand_total = round(grand_total + round_off, 2)

        db.session.flush()
        _record_inventory(voucher, action='add')

        db.session.commit()
        flash('Purchase Voucher updated.', 'success')
        return redirect(url_for('purchase.view_purchase', vid=voucher.id))

    suppliers = Supplier.query.order_by(Supplier.name).all()
    account_heads = AccountHead.query.order_by(AccountHead.account_type, AccountHead.name).all()
    products = Product.query.order_by(Product.name).all()
    company = CompanySettings.query.first()
    company_state_code = company.state_code if company else ''
    return render_template('purchase/form.html',
                           voucher=voucher,
                           edit_mode=True,
                           suppliers=suppliers,
                           account_heads=account_heads,
                           products=products,
                           voucher_types=VOUCHER_TYPES,
                           payment_modes=PAYMENT_MODES,
                           payment_statuses=PAYMENT_STATUSES,
                           gst_rates=GST_RATES,
                           units=UNITS,
                           company_state_code=company_state_code)


@purchase_bp.route('/<int:vid>')
def view_purchase(vid):
    voucher = PurchaseVoucher.query.get_or_404(vid)
    return render_template('purchase/view.html', voucher=voucher)


@purchase_bp.route('/<int:vid>/delete', methods=['POST'])
def delete_purchase(vid):
    voucher = PurchaseVoucher.query.get_or_404(vid)

    # Reverse stock changes before deleting
    _record_inventory(voucher, action='remove')
    if voucher.voucher_type == 'Regular':
        for item in voucher.items:
            if item.product_id:
                prod = Product.query.get(item.product_id)
                if prod:
                    prod.stock_quantity = max(0.0, (prod.stock_quantity or 0.0) - item.quantity)

    db.session.delete(voucher)
    db.session.commit()
    flash('Purchase Voucher deleted.', 'info')
    return redirect(url_for('purchase.list_purchases'))


@purchase_bp.route('/api/supplier/<int:sid>')
def api_supplier(sid):
    """Return supplier details as JSON."""
    s = Supplier.query.get_or_404(sid)
    return jsonify(s.to_dict())


@purchase_bp.route('/api/products')
def api_products():
    """Search products for purchase item dropdown."""
    q = request.args.get('q', '')
    products = Product.query
    if q:
        products = products.filter(
            Product.name.ilike(f'%{q}%') |
            Product.catalog_no.ilike(f'%{q}%')
        )
    products = products.order_by(Product.name).limit(20).all()
    return jsonify([p.to_dict() for p in products])
