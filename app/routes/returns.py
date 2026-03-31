"""
Purchase Return and Sales Return voucher routes.
"""
from datetime import datetime, date
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify)
from app import db
from app.models import (PurchaseReturn, PurchaseReturnItem,
                        SalesReturn, SalesReturnItem,
                        PurchaseVoucher, Invoice,
                        Supplier, Customer, Product,
                        AccountHead, InventoryLedger)
from app.services.invoice_numbering import get_next_invoice_number, peek_next_invoice_number

returns_bp = Blueprint('returns', __name__)

GST_RATES = [0, 5, 12, 18, 28]
UNITS = ['Pcs', 'Nos', 'Kg', 'Ltr', 'Mtr', 'Box', 'Set', 'Pair', 'Roll', 'Sheet']


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _parse_return_items(request, is_igst):
    product_ids = request.form.getlist('product_id[]')
    descriptions = request.form.getlist('description[]')
    hsn_codes = request.form.getlist('hsn_code[]')
    gst_rates = request.form.getlist('gst_rate[]')
    quantities = request.form.getlist('quantity[]')
    units = request.form.getlist('unit[]')
    unit_prices = request.form.getlist('unit_price[]')

    items = []
    subtotal = cgst_total = sgst_total = igst_total = 0.0

    for i, desc in enumerate(descriptions):
        if not desc.strip():
            continue
        qty = float(quantities[i] if i < len(quantities) else 0) or 0.0
        price = float(unit_prices[i] if i < len(unit_prices) else 0) or 0.0
        gst_rate = float(gst_rates[i] if i < len(gst_rates) else 0) or 0.0
        amount = qty * price
        subtotal += amount

        cgst_amt = sgst_amt = igst_amt = 0.0
        if is_igst:
            igst_amt = round(amount * gst_rate / 100, 2)
            igst_total += igst_amt
        else:
            cgst_amt = round(amount * gst_rate / 200, 2)
            sgst_amt = cgst_amt
            cgst_total += cgst_amt
            sgst_total += sgst_amt

        pid_raw = product_ids[i] if i < len(product_ids) else ''
        pid = int(pid_raw) if pid_raw and pid_raw.strip().isdigit() else None

        items.append(dict(
            sl_no=len(items) + 1,
            product_id=pid,
            description=desc.strip(),
            hsn_code=hsn_codes[i] if i < len(hsn_codes) else '',
            gst_rate=gst_rate,
            quantity=qty,
            unit=units[i] if i < len(units) else 'Pcs',
            unit_price=price,
            amount=amount,
            cgst_amount=cgst_amt,
            sgst_amount=sgst_amt,
            igst_amount=igst_amt,
        ))

    return items, subtotal, cgst_total, sgst_total, igst_total


# ---------------------------------------------------------------------------
# Purchase Returns
# ---------------------------------------------------------------------------

@returns_bp.route('/purchase/')
def list_purchase_returns():
    returns = PurchaseReturn.query.order_by(PurchaseReturn.date.desc()).all()
    total = sum(r.grand_total for r in returns)
    return render_template('returns/purchase_list.html', returns=returns, total=total)


@returns_bp.route('/purchase/create', methods=['GET', 'POST'])
def create_purchase_return():
    if request.method == 'POST':
        data = request.form
        ret_date = datetime.strptime(
            data.get('date', date.today().strftime('%Y-%m-%d')), '%Y-%m-%d'
        ).date()
        is_igst = data.get('is_igst') == 'on'
        return_no = get_next_invoice_number('PR')

        orig_id = data.get('original_voucher_id') or None
        supplier_id = data.get('supplier_id') or None

        ret = PurchaseReturn(
            return_no=return_no,
            date=ret_date,
            original_voucher_id=int(orig_id) if orig_id else None,
            supplier_id=int(supplier_id) if supplier_id else None,
            supplier_name=data.get('supplier_name', ''),
            supplier_gstin=data.get('supplier_gstin', ''),
            reason=data.get('reason', ''),
            is_igst=is_igst,
            notes=data.get('notes', ''),
        )

        parsed_items, subtotal, cgst_total, sgst_total, igst_total = _parse_return_items(request, is_igst)
        for item_data in parsed_items:
            item = PurchaseReturnItem(
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
            )
            ret.items.append(item)

        grand_total = subtotal + cgst_total + sgst_total + igst_total
        ret.subtotal = round(subtotal, 2)
        ret.cgst_total = round(cgst_total, 2)
        ret.sgst_total = round(sgst_total, 2)
        ret.igst_total = round(igst_total, 2)
        ret.grand_total = round(grand_total, 2)

        db.session.add(ret)
        db.session.flush()

        # Inventory: purchase return decreases stock (qty_out)
        for item_data in parsed_items:
            if item_data['product_id']:
                prod = Product.query.get(item_data['product_id'])
                if prod:
                    prod.stock_quantity = max(0.0, (prod.stock_quantity or 0.0) - item_data['quantity'])
                entry = InventoryLedger(
                    date=ret_date,
                    product_id=item_data['product_id'],
                    qty_in=0.0,
                    qty_out=item_data['quantity'],
                    source_type='purchase_return',
                    source_id=ret.id,
                    notes=f'Purchase Return {return_no}',
                )
                db.session.add(entry)

        db.session.commit()
        flash(f'Purchase Return {return_no} created.', 'success')
        return redirect(url_for('returns.list_purchase_returns'))

    suppliers = Supplier.query.order_by(Supplier.name).all()
    vouchers = PurchaseVoucher.query.order_by(PurchaseVoucher.date.desc()).limit(50).all()
    products = Product.query.order_by(Product.name).all()
    return render_template('returns/purchase_form.html',
                           today=date.today().strftime('%Y-%m-%d'),
                           next_no=peek_next_invoice_number('PR'),
                           suppliers=suppliers,
                           vouchers=vouchers,
                           products=products,
                           gst_rates=GST_RATES,
                           units=UNITS)


@returns_bp.route('/purchase/<int:rid>/delete', methods=['POST'])
def delete_purchase_return(rid):
    ret = PurchaseReturn.query.get_or_404(rid)
    # Reverse stock: add back
    for item in ret.items:
        if item.product_id:
            prod = Product.query.get(item.product_id)
            if prod:
                prod.stock_quantity = (prod.stock_quantity or 0.0) + item.quantity
    InventoryLedger.query.filter_by(source_type='purchase_return', source_id=ret.id).delete()
    db.session.delete(ret)
    db.session.commit()
    flash('Purchase Return deleted.', 'info')
    return redirect(url_for('returns.list_purchase_returns'))


# ---------------------------------------------------------------------------
# Sales Returns
# ---------------------------------------------------------------------------

@returns_bp.route('/sales/')
def list_sales_returns():
    returns = SalesReturn.query.order_by(SalesReturn.date.desc()).all()
    total = sum(r.grand_total for r in returns)
    return render_template('returns/sales_list.html', returns=returns, total=total)


@returns_bp.route('/sales/create', methods=['GET', 'POST'])
def create_sales_return():
    if request.method == 'POST':
        data = request.form
        ret_date = datetime.strptime(
            data.get('date', date.today().strftime('%Y-%m-%d')), '%Y-%m-%d'
        ).date()
        is_igst = data.get('is_igst') == 'on'
        return_no = get_next_invoice_number('SR')

        orig_id = data.get('original_invoice_id') or None
        customer_id = data.get('customer_id') or None

        ret = SalesReturn(
            return_no=return_no,
            date=ret_date,
            original_invoice_id=int(orig_id) if orig_id else None,
            customer_id=int(customer_id) if customer_id else None,
            customer_name=data.get('customer_name', ''),
            customer_gstin=data.get('customer_gstin', ''),
            reason=data.get('reason', ''),
            is_igst=is_igst,
            notes=data.get('notes', ''),
        )

        parsed_items, subtotal, cgst_total, sgst_total, igst_total = _parse_return_items(request, is_igst)
        for item_data in parsed_items:
            item = SalesReturnItem(
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
            )
            ret.items.append(item)

        grand_total = subtotal + cgst_total + sgst_total + igst_total
        ret.subtotal = round(subtotal, 2)
        ret.cgst_total = round(cgst_total, 2)
        ret.sgst_total = round(sgst_total, 2)
        ret.igst_total = round(igst_total, 2)
        ret.grand_total = round(grand_total, 2)

        db.session.add(ret)
        db.session.flush()

        # Inventory: sales return increases stock (qty_in)
        for item_data in parsed_items:
            if item_data['product_id']:
                prod = Product.query.get(item_data['product_id'])
                if prod:
                    prod.stock_quantity = (prod.stock_quantity or 0.0) + item_data['quantity']
                entry = InventoryLedger(
                    date=ret_date,
                    product_id=item_data['product_id'],
                    qty_in=item_data['quantity'],
                    qty_out=0.0,
                    source_type='sales_return',
                    source_id=ret.id,
                    notes=f'Sales Return {return_no}',
                )
                db.session.add(entry)

        db.session.commit()
        flash(f'Sales Return {return_no} created.', 'success')
        return redirect(url_for('returns.list_sales_returns'))

    customers = Customer.query.order_by(Customer.name).all()
    invoices = Invoice.query.order_by(Invoice.date.desc()).limit(50).all()
    products = Product.query.order_by(Product.name).all()
    return render_template('returns/sales_form.html',
                           today=date.today().strftime('%Y-%m-%d'),
                           next_no=peek_next_invoice_number('SR'),
                           customers=customers,
                           invoices=invoices,
                           products=products,
                           gst_rates=GST_RATES,
                           units=UNITS)


@returns_bp.route('/sales/<int:rid>/delete', methods=['POST'])
def delete_sales_return(rid):
    ret = SalesReturn.query.get_or_404(rid)
    # Reverse stock: deduct
    for item in ret.items:
        if item.product_id:
            prod = Product.query.get(item.product_id)
            if prod:
                prod.stock_quantity = max(0.0, (prod.stock_quantity or 0.0) - item.quantity)
    InventoryLedger.query.filter_by(source_type='sales_return', source_id=ret.id).delete()
    db.session.delete(ret)
    db.session.commit()
    flash('Sales Return deleted.', 'info')
    return redirect(url_for('returns.list_sales_returns'))
