"""
Delivery Challan routes.
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, send_file)
from app import db
from app.models import Invoice, CompanySettings
from app.services.pdf_generator import generate_challan_pdf

challan_bp = Blueprint('challan', __name__)


@challan_bp.route('/<int:invoice_id>/pdf')
def download_challan_pdf(invoice_id):
    """Download the Delivery Challan PDF for an invoice."""
    invoice = Invoice.query.get_or_404(invoice_id)
    pdf_data, ext = generate_challan_pdf(invoice)
    fname = f"Challan_{(invoice.challan_no or invoice.invoice_no).replace('/', '_')}.{ext}"
    if ext == 'pdf':
        from io import BytesIO
        return send_file(BytesIO(pdf_data), mimetype='application/pdf',
                         as_attachment=False, download_name=fname)
    from flask import Response
    return Response(pdf_data, mimetype='text/html')


@challan_bp.route('/list')
def list_challans():
    """List all invoices that have an associated challan."""
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    settings = CompanySettings.query.first()
    return render_template('challan/list.html', invoices=invoices, settings=settings)
