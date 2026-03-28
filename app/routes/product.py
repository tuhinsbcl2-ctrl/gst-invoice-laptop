"""
Product / Inventory management routes.
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify)
from app import db
from app.models import Product

product_bp = Blueprint('product', __name__)


@product_bp.route('/')
def list_products():
    q = request.args.get('q', '')
    products = Product.query
    if q:
        products = products.filter(
            Product.name.ilike(f'%{q}%') |
            Product.catalog_no.ilike(f'%{q}%') |
            Product.hsn_code.ilike(f'%{q}%')
        )
    products = products.order_by(Product.name).all()
    low_stock = [p for p in products if p.stock_quantity <= p.low_stock_threshold]
    return render_template('product/list.html', products=products, q=q, low_stock=low_stock)


@product_bp.route('/create', methods=['GET', 'POST'])
def create_product():
    if request.method == 'POST':
        data = request.form
        p = Product(
            catalog_no=data.get('catalog_no', ''),
            name=data.get('name', ''),
            hsn_code=data.get('hsn_code', ''),
            default_gst_rate=float(data.get('default_gst_rate', 5.0) or 5.0),
            default_unit_price=float(data.get('default_unit_price', 0.0) or 0.0),
            unit=data.get('unit', 'Pcs'),
            stock_quantity=float(data.get('stock_quantity', 0.0) or 0.0),
            low_stock_threshold=float(data.get('low_stock_threshold', 10.0) or 10.0),
        )
        db.session.add(p)
        db.session.commit()
        flash(f'Product "{p.name}" created.', 'success')
        return redirect(url_for('product.list_products'))
    return render_template('product/form.html')


@product_bp.route('/<int:pid>/edit', methods=['GET', 'POST'])
def edit_product(pid):
    p = Product.query.get_or_404(pid)
    if request.method == 'POST':
        data = request.form
        p.catalog_no = data.get('catalog_no', '')
        p.name = data.get('name', '')
        p.hsn_code = data.get('hsn_code', '')
        p.default_gst_rate = float(data.get('default_gst_rate', 5.0) or 5.0)
        p.default_unit_price = float(data.get('default_unit_price', 0.0) or 0.0)
        p.unit = data.get('unit', 'Pcs')
        p.stock_quantity = float(data.get('stock_quantity', 0.0) or 0.0)
        p.low_stock_threshold = float(data.get('low_stock_threshold', 10.0) or 10.0)
        db.session.commit()
        flash('Product updated.', 'success')
        return redirect(url_for('product.list_products'))
    return render_template('product/form.html', product=p, edit_mode=True)


@product_bp.route('/<int:pid>/delete', methods=['POST'])
def delete_product(pid):
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash('Product deleted.', 'info')
    return redirect(url_for('product.list_products'))


@product_bp.route('/api/search')
def api_search():
    q = request.args.get('q', '')
    products = Product.query.filter(
        Product.name.ilike(f'%{q}%') |
        Product.catalog_no.ilike(f'%{q}%')
    ).limit(10).all()
    return jsonify([p.to_dict() for p in products])
