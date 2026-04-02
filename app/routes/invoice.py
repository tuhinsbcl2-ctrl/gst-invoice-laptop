"""
Invoice CRUD routes.
"""
import os
from datetime import datetime, date
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, send_file, current_app)
from app import db
from app.models import Invoice, InvoiceItem, Customer, Product, CompanySettings
from app.services.gst_calculator import (calculate_invoice_totals,
                                          is_igst_applicable, get_hsn_breakup)
from app.services.invoice_numbering import get_next_invoice_number, peek_next_invoice_number
from app.services.number_to_words import amount_to_words
from app.services.pdf_generator import generate_invoice_pdf, generate_combined_pdf
from app.services.excel_export import export_invoices_excel, export_invoices_csv

invoice_bp = Blueprint('invoice', __name__)


@invoice_bp.route('/')
def list_invoices():
    q = request.args.get('q', '')
    status = request.args.get('status', '')
    invoices = Invoice.query
    if q:
        invoices = invoices.filter(
            Invoice.invoice_no.ilike(f'%{q}%') |
            Invoice.buyer_name.ilike(f'%{q}%')
        )
    if status:
        invoices = invoices.filter(Invoice.payment_status == status)
    invoices = invoices.order_by(Invoice.created_at.desc()).all()
    return render_template('invoice/list.html', invoices=invoices, q=q, status=status)


@invoice_bp.route('/create', methods=['GET', 'POST'])
def create_invoice():
    settings = CompanySettings.query.first()
    customers = Customer.query.order_by(Customer.name).all()
    products = Product.query.order_by(Product.name).all()

    if request.method == 'POST':
        data = request.form

        # Determine IGST
        place_code = data.get('place_of_supply_code', '19')
        seller_code = settings.state_code if settings else '19'
        is_igst = is_igst_applicable(seller_code, place_code)

        # Collect line items
        items_raw = _collect_items_from_form(data)
        processed_items, totals = calculate_invoice_totals(items_raw, is_igst)

        # Generate invoice number
        prefix = settings.invoice_prefix if settings else 'NE'
        inv_date_str = data.get('date', date.today().strftime('%Y-%m-%d'))
        inv_date = datetime.strptime(inv_date_str, '%Y-%m-%d').date()
        invoice_no = get_next_invoice_number(prefix, inv_date)

        # Amount in words
        total_tax = totals['cgst_total'] + totals['sgst_total'] + totals['igst_total']
        words = amount_to_words(totals['grand_total'])
        tax_words = amount_to_words(total_tax)

        # Buyer order date
        bod_str = data.get('buyer_order_date', '')
        buyer_order_date = None
        if bod_str:
            try:
                buyer_order_date = datetime.strptime(bod_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Challan date
        cd_str = data.get('challan_date', '')
        challan_date = None
        if cd_str:
            try:
                challan_date = datetime.strptime(cd_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        invoice = Invoice(
            invoice_no=invoice_no,
            date=inv_date,
            challan_no=data.get('challan_no', ''),
            challan_date=challan_date,
            buyer_id=data.get('buyer_id') or None,
            buyer_name=data.get('buyer_name', ''),
            buyer_address=data.get('buyer_address', ''),
            buyer_gstin=data.get('buyer_gstin', ''),
            buyer_state_name=data.get('buyer_state_name', ''),
            buyer_state_code=data.get('buyer_state_code', ''),
            buyer_order_no=data.get('buyer_order_no', ''),
            buyer_order_date=buyer_order_date,
            reference_no_date=data.get('reference_no_date', ''),
            other_references=data.get('other_references', ''),
            other_document_no=data.get('other_document_no', ''),
            dispatched_through=data.get('dispatched_through', ''),
            destination=data.get('destination', ''),
            bill_of_lading=data.get('bill_of_lading', ''),
            motor_vehicle_no=data.get('motor_vehicle_no', ''),
            terms_of_delivery=data.get('terms_of_delivery', ''),
            payment_mode=data.get('payment_mode', 'Bank'),
            payment_status=data.get('payment_status', 'Unpaid'),
            place_of_supply=data.get('place_of_supply', ''),
            place_of_supply_code=place_code,
            is_igst=is_igst,
            ship_to_same=data.get('ship_to_same') == 'on',
            ship_to_name=data.get('ship_to_name', ''),
            ship_to_address=data.get('ship_to_address', ''),
            ship_to_state=data.get('ship_to_state', ''),
            ship_to_gstin=data.get('ship_to_gstin', ''),
            way_bill_no=data.get('way_bill_no', ''),
            subtotal=totals['subtotal'],
            cgst_total=totals['cgst_total'],
            sgst_total=totals['sgst_total'],
            igst_total=totals['igst_total'],
            round_off=totals['round_off'],
            grand_total=totals['grand_total'],
            amount_in_words=words,
            tax_amount_in_words=tax_words,
            notes=data.get('notes', ''),
        )
        db.session.add(invoice)
        db.session.flush()

        # Deduct stock and save items
        for item_data in processed_items:
            item = InvoiceItem(
                invoice_id=invoice.id,
                sl_no=item_data.get('sl_no'),
                catalog_no=item_data.get('catalog_no', ''),
                description=item_data.get('description', ''),
                hsn_code=item_data.get('hsn_code', ''),
                gst_rate=item_data.get('gst_rate', 0),
                quantity=item_data.get('quantity', 0),
                unit=item_data.get('unit', 'Pcs'),
                unit_price=item_data.get('unit_price', 0),
                amount=item_data.get('amount', 0),
                cgst_rate=item_data.get('cgst_rate', 0),
                cgst_amount=item_data.get('cgst_amount', 0),
                sgst_rate=item_data.get('sgst_rate', 0),
                sgst_amount=item_data.get('sgst_amount', 0),
                igst_rate=item_data.get('igst_rate', 0),
                igst_amount=item_data.get('igst_amount', 0),
                lot_no=item_data.get('lot_no', ''),
                mfg_date=item_data.get('mfg_date', ''),
                exp_date=item_data.get('exp_date', ''),
            )
            db.session.add(item)

            # Deduct product stock
            product_id = item_data.get('product_id')
            if product_id:
                prod = Product.query.get(product_id)
                if prod:
                    prod.stock_quantity = max(0, prod.stock_quantity - float(item_data.get('quantity', 0)))

        db.session.commit()
        flash(f'Invoice {invoice_no} created successfully!', 'success')
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice.id))

    # GET – show form
    next_no = peek_next_invoice_number(
        settings.invoice_prefix if settings else 'NE'
    )
    return render_template('invoice/create.html',
                           settings=settings,
                           customers=customers,
                           products=products,
                           next_invoice_no=next_no,
                           today=date.today().strftime('%Y-%m-%d'))


@invoice_bp.route('/<int:invoice_id>')
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    settings = CompanySettings.query.first()
    hsn_breakup = get_hsn_breakup(
        [item.to_dict() for item in invoice.items],
        is_igst=invoice.is_igst
    )
    return render_template('invoice/view.html',
                           invoice=invoice,
                           settings=settings,
                           hsn_breakup=hsn_breakup)


@invoice_bp.route('/<int:invoice_id>/edit', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    settings = CompanySettings.query.first()
    customers = Customer.query.order_by(Customer.name).all()
    products = Product.query.order_by(Product.name).all()

    if request.method == 'POST':
        data = request.form
        place_code = data.get('place_of_supply_code', '19')
        seller_code = settings.state_code if settings else '19'
        is_igst = is_igst_applicable(seller_code, place_code)

        items_raw = _collect_items_from_form(data)
        processed_items, totals = calculate_invoice_totals(items_raw, is_igst)

        total_tax = totals['cgst_total'] + totals['sgst_total'] + totals['igst_total']
        words = amount_to_words(totals['grand_total'])
        tax_words = amount_to_words(total_tax)

        inv_date_str = data.get('date', date.today().strftime('%Y-%m-%d'))
        inv_date = datetime.strptime(inv_date_str, '%Y-%m-%d').date()

        bod_str = data.get('buyer_order_date', '')
        buyer_order_date = None
        if bod_str:
            try:
                buyer_order_date = datetime.strptime(bod_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        cd_str = data.get('challan_date', '')
        challan_date = None
        if cd_str:
            try:
                challan_date = datetime.strptime(cd_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        invoice.date = inv_date
        invoice.challan_no = data.get('challan_no', '')
        invoice.challan_date = challan_date
        invoice.buyer_id = data.get('buyer_id') or None
        invoice.buyer_name = data.get('buyer_name', '')
        invoice.buyer_address = data.get('buyer_address', '')
        invoice.buyer_gstin = data.get('buyer_gstin', '')
        invoice.buyer_state_name = data.get('buyer_state_name', '')
        invoice.buyer_state_code = data.get('buyer_state_code', '')
        invoice.buyer_order_no = data.get('buyer_order_no', '')
        invoice.buyer_order_date = buyer_order_date
        invoice.reference_no_date = data.get('reference_no_date', '')
        invoice.other_references = data.get('other_references', '')
        invoice.other_document_no = data.get('other_document_no', '')
        invoice.dispatched_through = data.get('dispatched_through', '')
        invoice.destination = data.get('destination', '')
        invoice.bill_of_lading = data.get('bill_of_lading', '')
        invoice.motor_vehicle_no = data.get('motor_vehicle_no', '')
        invoice.terms_of_delivery = data.get('terms_of_delivery', '')
        invoice.payment_mode = data.get('payment_mode', 'Bank')
        invoice.payment_status = data.get('payment_status', 'Unpaid')
        invoice.place_of_supply = data.get('place_of_supply', '')
        invoice.place_of_supply_code = place_code
        invoice.is_igst = is_igst
        invoice.ship_to_same = data.get('ship_to_same') == 'on'
        invoice.ship_to_name = data.get('ship_to_name', '')
        invoice.ship_to_address = data.get('ship_to_address', '')
        invoice.ship_to_state = data.get('ship_to_state', '')
        invoice.ship_to_gstin = data.get('ship_to_gstin', '')
        invoice.way_bill_no = data.get('way_bill_no', '')
        invoice.subtotal = totals['subtotal']
        invoice.cgst_total = totals['cgst_total']
        invoice.sgst_total = totals['sgst_total']
        invoice.igst_total = totals['igst_total']
        invoice.round_off = totals['round_off']
        invoice.grand_total = totals['grand_total']
        invoice.amount_in_words = words
        invoice.tax_amount_in_words = tax_words
        invoice.notes = data.get('notes', '')
        invoice.updated_at = datetime.utcnow()

        # Replace items
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        for item_data in processed_items:
            item = InvoiceItem(
                invoice_id=invoice.id,
                sl_no=item_data.get('sl_no'),
                catalog_no=item_data.get('catalog_no', ''),
                description=item_data.get('description', ''),
                hsn_code=item_data.get('hsn_code', ''),
                gst_rate=item_data.get('gst_rate', 0),
                quantity=item_data.get('quantity', 0),
                unit=item_data.get('unit', 'Pcs'),
                unit_price=item_data.get('unit_price', 0),
                amount=item_data.get('amount', 0),
                cgst_rate=item_data.get('cgst_rate', 0),
                cgst_amount=item_data.get('cgst_amount', 0),
                sgst_rate=item_data.get('sgst_rate', 0),
                sgst_amount=item_data.get('sgst_amount', 0),
                igst_rate=item_data.get('igst_rate', 0),
                igst_amount=item_data.get('igst_amount', 0),
                lot_no=item_data.get('lot_no', ''),
                mfg_date=item_data.get('mfg_date', ''),
                exp_date=item_data.get('exp_date', ''),
            )
            db.session.add(item)

        db.session.commit()
        flash('Invoice updated successfully!', 'success')
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice.id))

    return render_template('invoice/create.html',
                           invoice=invoice,
                           settings=settings,
                           customers=customers,
                           products=products,
                           edit_mode=True)


@invoice_bp.route('/<int:invoice_id>/delete', methods=['POST'])
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    db.session.delete(invoice)
    db.session.commit()
    flash('Invoice deleted.', 'info')
    return redirect(url_for('invoice.list_invoices'))


@invoice_bp.route('/<int:invoice_id>/pdf')
def download_pdf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    pdf_data, ext = generate_invoice_pdf(invoice)
    fname = f"Invoice_{invoice.invoice_no.replace('/', '_')}.{ext}"
    if ext == 'pdf':
        from io import BytesIO
        return send_file(BytesIO(pdf_data), mimetype='application/pdf',
                         as_attachment=False, download_name=fname)
    # Fallback: return HTML
    from flask import Response
    return Response(pdf_data, mimetype='text/html')


@invoice_bp.route('/<int:invoice_id>/combined_pdf')
def combined_pdf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    pdf_data, ext = generate_combined_pdf(invoice)
    fname = f"Combined_{invoice.invoice_no.replace('/', '_')}.{ext}"
    if ext == 'pdf':
        from io import BytesIO
        return send_file(BytesIO(pdf_data), mimetype='application/pdf',
                         as_attachment=False, download_name=fname)
    from flask import Response
    return Response(pdf_data, mimetype='text/html')


@invoice_bp.route('/<int:invoice_id>/mark_paid', methods=['POST'])
def mark_paid(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.payment_status = 'Paid'
    db.session.commit()
    flash('Invoice marked as Paid.', 'success')
    return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))


@invoice_bp.route('/export/excel')
def export_excel():
    invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    data, ext = export_invoices_excel(invoices)
    from io import BytesIO
    return send_file(BytesIO(data),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if ext == 'xlsx' else 'text/csv',
                     as_attachment=True,
                     download_name=f'invoices.{ext}')


@invoice_bp.route('/export/csv')
def export_csv():
    invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    data, ext = export_invoices_csv(invoices)
    from io import BytesIO
    return send_file(BytesIO(data), mimetype='text/csv',
                     as_attachment=True, download_name='invoices.csv')


@invoice_bp.route('/api/next_number')
def api_next_number():
    settings = CompanySettings.query.first()
    prefix = settings.invoice_prefix if settings else 'NE'
    date_str = request.args.get('date', '')
    ref_date = None
    if date_str:
        try:
            ref_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    return jsonify({'next': peek_next_invoice_number(prefix, ref_date)})


@invoice_bp.route('/api/customer/<int:cid>')
def api_customer(cid):
    c = Customer.query.get_or_404(cid)
    return jsonify(c.to_dict())


@invoice_bp.route('/api/product/<int:pid>')
def api_product(pid):
    p = Product.query.get_or_404(pid)
    return jsonify(p.to_dict())


@invoice_bp.route('/api/calculate', methods=['POST'])
def api_calculate():
    data = request.get_json()
    items = data.get('items', [])
    is_igst = data.get('is_igst', False)
    processed, totals = calculate_invoice_totals(items, is_igst)
    total_tax = totals['cgst_total'] + totals['sgst_total'] + totals['igst_total']
    totals['amount_in_words'] = amount_to_words(totals['grand_total'])
    totals['tax_amount_in_words'] = amount_to_words(total_tax)
    totals['items'] = processed
    return jsonify(totals)


def _collect_items_from_form(data):
    """Extract line items from a multivalue form POST."""
    items = []
    descriptions = data.getlist('description[]')
    for i, desc in enumerate(descriptions):
        if not desc.strip():
            continue
        items.append({
            'catalog_no': _safe_list(data.getlist('catalog_no[]'), i),
            'description': desc,
            'hsn_code': _safe_list(data.getlist('hsn_code[]'), i),
            'gst_rate': float(_safe_list(data.getlist('gst_rate[]'), i, '0') or '0'),
            'quantity': float(_safe_list(data.getlist('quantity[]'), i, '0') or '0'),
            'unit': _safe_list(data.getlist('unit[]'), i, 'Pcs'),
            'unit_price': float(_safe_list(data.getlist('unit_price[]'), i, '0') or '0'),
            'lot_no': _safe_list(data.getlist('lot_no[]'), i),
            'mfg_date': _safe_list(data.getlist('mfg_date[]'), i),
            'exp_date': _safe_list(data.getlist('exp_date[]'), i),
            'product_id': _safe_list(data.getlist('product_id[]'), i),
        })
    return items


def _safe_list(lst, idx, default=''):
    try:
        return lst[idx] if lst[idx] is not None else default
    except IndexError:
        return default
