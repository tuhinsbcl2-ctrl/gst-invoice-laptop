"""
Quotation CRUD routes.
"""
from datetime import datetime, date
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, send_file)
from app import db
from app.models import Quotation, QuotationItem, Customer, Product, CompanySettings
from app.services.number_to_words import amount_to_words
from app.services.pdf_generator import generate_quotation_pdf

quotation_bp = Blueprint('quotation', __name__)


def _get_next_quotation_number():
    """Generate the next quotation number in QT/NNN/YY-YY format."""
    from app.services.invoice_numbering import get_financial_year
    fy = get_financial_year()
    count = Quotation.query.count()
    serial = str(count + 1).zfill(3)
    return f"QT/{serial}/{fy}"


def _peek_next_quotation_number():
    """Preview the next quotation number without incrementing."""
    from app.services.invoice_numbering import get_financial_year
    fy = get_financial_year()
    count = Quotation.query.count()
    serial = str(count + 1).zfill(3)
    return f"QT/{serial}/{fy}"


def _collect_items_from_form(data):
    """Extract line items from a multivalue form POST."""
    items = []
    descriptions = data.getlist('description[]')
    for i, desc in enumerate(descriptions):
        if not desc.strip():
            continue
        def _safe(lst, idx, default=''):
            try:
                return lst[idx] if lst[idx] is not None else default
            except IndexError:
                return default

        items.append({
            'description': desc,
            'hsn_code': _safe(data.getlist('hsn_code[]'), i),
            'gst_rate': float(_safe(data.getlist('gst_rate[]'), i, '0') or '0'),
            'quantity': float(_safe(data.getlist('quantity[]'), i, '1') or '1'),
            'unit': _safe(data.getlist('unit[]'), i, 'Pcs'),
            'unit_price': float(_safe(data.getlist('unit_price[]'), i, '0') or '0'),
        })
    return items


def _calculate_totals(items_raw):
    """Calculate subtotal, CGST, SGST, grand total for quotation items."""
    processed = []
    subtotal = 0.0
    cgst_total = 0.0
    sgst_total = 0.0

    for i, item in enumerate(items_raw, start=1):
        amount = round(item['quantity'] * item['unit_price'], 2)
        gst_rate = item['gst_rate']
        cgst_rate = gst_rate / 2
        sgst_rate = gst_rate / 2
        cgst_amount = round(amount * cgst_rate / 100, 2)
        sgst_amount = round(amount * sgst_rate / 100, 2)

        subtotal += amount
        cgst_total += cgst_amount
        sgst_total += sgst_amount

        processed.append({
            'sl_no': i,
            'description': item['description'],
            'hsn_code': item['hsn_code'],
            'gst_rate': gst_rate,
            'quantity': item['quantity'],
            'unit': item['unit'],
            'unit_price': item['unit_price'],
            'amount': amount,
            'cgst_rate': cgst_rate,
            'cgst_amount': cgst_amount,
            'sgst_rate': sgst_rate,
            'sgst_amount': sgst_amount,
        })

    grand_total = round(subtotal + cgst_total + sgst_total, 2)
    return processed, {
        'subtotal': round(subtotal, 2),
        'cgst_total': round(cgst_total, 2),
        'sgst_total': round(sgst_total, 2),
        'grand_total': grand_total,
    }


def _dynamic_subject(items_raw):
    """Derive the quotation subject from items (Point 4 – Data Consistency)."""
    descs = [it['description'] for it in items_raw if it.get('description')]
    if not descs:
        return 'Goods & Services'
    if len(descs) == 1:
        return descs[0]
    return 'Medical Equipments & Supplies'


@quotation_bp.route('/')
def list_quotations():
    q = request.args.get('q', '')
    quotations = Quotation.query
    if q:
        quotations = quotations.filter(
            Quotation.quotation_no.ilike(f'%{q}%') |
            Quotation.customer_name.ilike(f'%{q}%')
        )
    quotations = quotations.order_by(Quotation.created_at.desc()).all()
    return render_template('quotation/list.html', quotations=quotations, q=q)


@quotation_bp.route('/create', methods=['GET', 'POST'])
def create_quotation():
    customers = Customer.query.order_by(Customer.name).all()
    products = Product.query.order_by(Product.name).all()

    if request.method == 'POST':
        data = request.form
        items_raw = _collect_items_from_form(data)
        processed_items, totals = _calculate_totals(items_raw)

        # Point 4: Dynamic subject – auto-derived unless user provided one
        subject = data.get('subject', '').strip() or _dynamic_subject(items_raw)

        qt_no = _get_next_quotation_number()
        date_str = data.get('date', date.today().strftime('%Y-%m-%d'))
        qt_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        quotation = Quotation(
            quotation_no=qt_no,
            date=qt_date,
            customer_id=data.get('customer_id') or None,
            customer_name=data.get('customer_name', ''),
            customer_address=data.get('customer_address', ''),
            customer_gstin=data.get('customer_gstin', ''),
            subject=subject,
            validity_days=int(data.get('validity_days', 15) or 15),
            subtotal=totals['subtotal'],
            cgst_total=totals['cgst_total'],
            sgst_total=totals['sgst_total'],
            grand_total=totals['grand_total'],
            amount_in_words=amount_to_words(totals['grand_total']),
            notes=data.get('notes', ''),
            status=data.get('status', 'Draft'),
        )
        db.session.add(quotation)
        db.session.flush()

        for item_data in processed_items:
            item = QuotationItem(
                quotation_id=quotation.id,
                sl_no=item_data['sl_no'],
                description=item_data['description'],
                hsn_code=item_data['hsn_code'],
                gst_rate=item_data['gst_rate'],
                quantity=item_data['quantity'],
                unit=item_data['unit'],
                unit_price=item_data['unit_price'],
                amount=item_data['amount'],
                cgst_rate=item_data['cgst_rate'],
                cgst_amount=item_data['cgst_amount'],
                sgst_rate=item_data['sgst_rate'],
                sgst_amount=item_data['sgst_amount'],
            )
            db.session.add(item)

        db.session.commit()
        flash(f'Quotation {qt_no} created successfully!', 'success')
        return redirect(url_for('quotation.view_quotation', quotation_id=quotation.id))

    next_no = _peek_next_quotation_number()
    return render_template('quotation/create.html',
                           customers=customers,
                           products=products,
                           next_quotation_no=next_no,
                           today=date.today().strftime('%Y-%m-%d'),
                           edit_mode=False)


@quotation_bp.route('/<int:quotation_id>')
def view_quotation(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    settings = CompanySettings.query.first()
    return render_template('quotation/view.html', quotation=quotation, settings=settings)


@quotation_bp.route('/<int:quotation_id>/edit', methods=['GET', 'POST'])
def edit_quotation(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    customers = Customer.query.order_by(Customer.name).all()
    products = Product.query.order_by(Product.name).all()

    if request.method == 'POST':
        data = request.form
        items_raw = _collect_items_from_form(data)
        processed_items, totals = _calculate_totals(items_raw)

        subject = data.get('subject', '').strip() or _dynamic_subject(items_raw)
        date_str = data.get('date', date.today().strftime('%Y-%m-%d'))
        qt_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        quotation.date = qt_date
        quotation.customer_id = data.get('customer_id') or None
        quotation.customer_name = data.get('customer_name', '')
        quotation.customer_address = data.get('customer_address', '')
        quotation.customer_gstin = data.get('customer_gstin', '')
        quotation.subject = subject
        quotation.validity_days = int(data.get('validity_days', 15) or 15)
        quotation.subtotal = totals['subtotal']
        quotation.cgst_total = totals['cgst_total']
        quotation.sgst_total = totals['sgst_total']
        quotation.grand_total = totals['grand_total']
        quotation.amount_in_words = amount_to_words(totals['grand_total'])
        quotation.notes = data.get('notes', '')
        quotation.status = data.get('status', quotation.status)

        # Replace items
        for old_item in list(quotation.items):
            db.session.delete(old_item)
        db.session.flush()

        for item_data in processed_items:
            item = QuotationItem(
                quotation_id=quotation.id,
                sl_no=item_data['sl_no'],
                description=item_data['description'],
                hsn_code=item_data['hsn_code'],
                gst_rate=item_data['gst_rate'],
                quantity=item_data['quantity'],
                unit=item_data['unit'],
                unit_price=item_data['unit_price'],
                amount=item_data['amount'],
                cgst_rate=item_data['cgst_rate'],
                cgst_amount=item_data['cgst_amount'],
                sgst_rate=item_data['sgst_rate'],
                sgst_amount=item_data['sgst_amount'],
            )
            db.session.add(item)

        db.session.commit()
        flash(f'Quotation {quotation.quotation_no} updated successfully!', 'success')
        return redirect(url_for('quotation.view_quotation', quotation_id=quotation.id))

    return render_template('quotation/create.html',
                           quotation=quotation,
                           customers=customers,
                           products=products,
                           today=date.today().strftime('%Y-%m-%d'),
                           edit_mode=True)


@quotation_bp.route('/<int:quotation_id>/delete', methods=['POST'])
def delete_quotation(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    db.session.delete(quotation)
    db.session.commit()
    flash('Quotation deleted.', 'info')
    return redirect(url_for('quotation.list_quotations'))


@quotation_bp.route('/<int:quotation_id>/pdf')
def download_pdf(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    pdf_data, ext = generate_quotation_pdf(quotation)
    fname = f"Quotation_{quotation.quotation_no.replace('/', '_')}.{ext}"
    if ext == 'pdf':
        from io import BytesIO
        return send_file(BytesIO(pdf_data), mimetype='application/pdf',
                         as_attachment=False, download_name=fname)
    from flask import Response
    return Response(pdf_data, mimetype='text/html')


@quotation_bp.route('/api/customer/<int:cid>')
def api_customer(cid):
    from flask import jsonify
    c = Customer.query.get_or_404(cid)
    return jsonify(c.to_dict())


@quotation_bp.route('/api/product/<int:pid>')
def api_product(pid):
    from flask import jsonify
    p = Product.query.get_or_404(pid)
    return jsonify(p.to_dict())
