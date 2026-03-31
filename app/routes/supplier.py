"""
Supplier management routes.
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify)
from app import db
from app.models import Supplier

supplier_bp = Blueprint('supplier', __name__)

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


@supplier_bp.route('/')
def list_suppliers():
    q = request.args.get('q', '')
    suppliers = Supplier.query
    if q:
        suppliers = suppliers.filter(
            Supplier.name.ilike(f'%{q}%') |
            Supplier.gstin.ilike(f'%{q}%')
        )
    suppliers = suppliers.order_by(Supplier.name).all()
    return render_template('supplier/list.html', suppliers=suppliers, q=q)


@supplier_bp.route('/create', methods=['GET', 'POST'])
def create_supplier():
    if request.method == 'POST':
        data = request.form
        s = Supplier(
            name=data.get('name', ''),
            address=data.get('address', ''),
            gstin=data.get('gstin', ''),
            pan=data.get('pan', ''),
            state_name=data.get('state_name', ''),
            state_code=data.get('state_code', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
        )
        db.session.add(s)
        db.session.commit()
        flash(f'Supplier "{s.name}" created.', 'success')
        return redirect(url_for('supplier.list_suppliers'))
    return render_template('supplier/form.html', states=INDIAN_STATES)


@supplier_bp.route('/<int:sid>/edit', methods=['GET', 'POST'])
def edit_supplier(sid):
    s = Supplier.query.get_or_404(sid)
    if request.method == 'POST':
        data = request.form
        s.name = data.get('name', '')
        s.address = data.get('address', '')
        s.gstin = data.get('gstin', '')
        s.pan = data.get('pan', '')
        s.state_name = data.get('state_name', '')
        s.state_code = data.get('state_code', '')
        s.phone = data.get('phone', '')
        s.email = data.get('email', '')
        db.session.commit()
        flash('Supplier updated.', 'success')
        return redirect(url_for('supplier.list_suppliers'))
    return render_template('supplier/form.html', supplier=s, states=INDIAN_STATES, edit_mode=True)


@supplier_bp.route('/<int:sid>/delete', methods=['POST'])
def delete_supplier(sid):
    s = Supplier.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    flash('Supplier deleted.', 'info')
    return redirect(url_for('supplier.list_suppliers'))


@supplier_bp.route('/api/search')
def api_search():
    q = request.args.get('q', '')
    suppliers = Supplier.query.filter(
        Supplier.name.ilike(f'%{q}%')
    ).limit(10).all()
    return jsonify([s.to_dict() for s in suppliers])
