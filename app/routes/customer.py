"""
Customer management routes.
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify)
from app import db
from app.models import Customer, Invoice

customer_bp = Blueprint('customer', __name__)

INDIAN_STATES = [
    ('01', 'Jammu & Kashmir'), ('02', 'Himachal Pradesh'), ('03', 'Punjab'),
    ('04', 'Chandigarh'), ('05', 'Uttarakhand'), ('06', 'Haryana'),
    ('07', 'Delhi'), ('08', 'Rajasthan'), ('09', 'Uttar Pradesh'),
    ('10', 'Bihar'), ('11', 'Sikkim'), ('12', 'Arunachal Pradesh'),
    ('13', 'Nagaland'), ('14', 'Manipur'), ('15', 'Mizoram'),
    ('16', 'Tripura'), ('17', 'Meghalaya'), ('18', 'Assam'),
    ('19', 'West Bengal'), ('20', 'Jharkhand'), ('21', 'Odisha'),
    ('22', 'Chhattisgarh'), ('23', 'Madhya Pradesh'), ('24', 'Gujarat'),
    ('25', 'Daman & Diu'), ('26', 'Dadra & Nagar Haveli'),
    ('27', 'Maharashtra'), ('28', 'Andhra Pradesh'), ('29', 'Karnataka'),
    ('30', 'Goa'), ('31', 'Lakshadweep'), ('32', 'Kerala'),
    ('33', 'Tamil Nadu'), ('34', 'Puducherry'), ('35', 'Andaman & Nicobar'),
    ('36', 'Telangana'), ('37', 'Andhra Pradesh (New)'),
]


@customer_bp.route('/')
def list_customers():
    q = request.args.get('q', '')
    customers = Customer.query
    if q:
        customers = customers.filter(
            Customer.name.ilike(f'%{q}%') |
            Customer.gstin.ilike(f'%{q}%')
        )
    customers = customers.order_by(Customer.name).all()
    return render_template('customer/list.html', customers=customers, q=q)


@customer_bp.route('/create', methods=['GET', 'POST'])
def create_customer():
    if request.method == 'POST':
        data = request.form
        c = Customer(
            name=data.get('name', ''),
            address=data.get('address', ''),
            gstin=data.get('gstin', ''),
            pan=data.get('pan', ''),
            state_name=data.get('state_name', ''),
            state_code=data.get('state_code', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
        )
        db.session.add(c)
        db.session.commit()
        flash(f'Customer "{c.name}" created.', 'success')
        return redirect(url_for('customer.list_customers'))
    return render_template('customer/form.html', states=INDIAN_STATES)


@customer_bp.route('/<int:cid>/edit', methods=['GET', 'POST'])
def edit_customer(cid):
    c = Customer.query.get_or_404(cid)
    if request.method == 'POST':
        data = request.form
        c.name = data.get('name', '')
        c.address = data.get('address', '')
        c.gstin = data.get('gstin', '')
        c.pan = data.get('pan', '')
        c.state_name = data.get('state_name', '')
        c.state_code = data.get('state_code', '')
        c.phone = data.get('phone', '')
        c.email = data.get('email', '')
        db.session.commit()
        flash('Customer updated.', 'success')
        return redirect(url_for('customer.list_customers'))
    return render_template('customer/form.html', customer=c, states=INDIAN_STATES, edit_mode=True)


@customer_bp.route('/<int:cid>/delete', methods=['POST'])
def delete_customer(cid):
    c = Customer.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    flash('Customer deleted.', 'info')
    return redirect(url_for('customer.list_customers'))


@customer_bp.route('/<int:cid>/ledger')
def ledger(cid):
    c = Customer.query.get_or_404(cid)
    invoices = Invoice.query.filter_by(buyer_id=cid).order_by(Invoice.date.desc()).all()
    total = sum(i.grand_total for i in invoices)
    paid = sum(i.grand_total for i in invoices if i.payment_status == 'Paid')
    outstanding = total - paid
    return render_template('customer/ledger.html', customer=c,
                           invoices=invoices, total=total,
                           paid=paid, outstanding=outstanding)


@customer_bp.route('/api/search')
def api_search():
    q = request.args.get('q', '')
    customers = Customer.query.filter(
        Customer.name.ilike(f'%{q}%')
    ).limit(10).all()
    return jsonify([c.to_dict() for c in customers])
