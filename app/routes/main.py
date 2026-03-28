"""
Main / Dashboard routes.
"""
from flask import Blueprint, render_template
from app.models import Invoice, Customer, Product, Expense
from app import db
from sqlalchemy import func
from datetime import date

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    total_invoices = Invoice.query.count()
    total_customers = Customer.query.count()
    total_products = Product.query.count()

    # Revenue this month
    today = date.today()
    month_invoices = Invoice.query.filter(
        func.strftime('%Y-%m', Invoice.date) == today.strftime('%Y-%m')
    ).all()
    month_revenue = sum(i.grand_total for i in month_invoices)

    # Outstanding
    unpaid = Invoice.query.filter(Invoice.payment_status.in_(['Unpaid', 'Partial'])).all()
    outstanding = sum(i.grand_total for i in unpaid)

    # Low stock products
    low_stock = Product.query.filter(
        Product.stock_quantity <= Product.low_stock_threshold
    ).all()

    # Recent invoices
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()

    return render_template('dashboard.html',
                           total_invoices=total_invoices,
                           total_customers=total_customers,
                           total_products=total_products,
                           month_revenue=month_revenue,
                           outstanding=outstanding,
                           low_stock=low_stock,
                           recent_invoices=recent_invoices)
