"""
PDF generation for Tax Invoice and Delivery Challan using WeasyPrint.
Renders HTML templates to PDF bytes.
"""
import os
from flask import render_template, current_app
from app.services.gst_calculator import get_hsn_breakup

try:
    from weasyprint import HTML, CSS
    _HAS_WEASYPRINT = True
except Exception:
    _HAS_WEASYPRINT = False


def generate_invoice_pdf(invoice):
    """Generate combined PDF (3 invoice copies) for a Tax Invoice."""
    from app.models import CompanySettings
    settings = CompanySettings.query.first()
    hsn_breakup = get_hsn_breakup(
        [item.to_dict() for item in invoice.items],
        is_igst=invoice.is_igst
    )
    copies = [
        'Original for Recipient',
        'Duplicate for Transporter',
        'Triplicate for Supplier',
    ]
    html_content = render_template(
        'invoice/pdf_template.html',
        invoice=invoice,
        settings=settings,
        hsn_breakup=hsn_breakup,
        copies=copies,
    )
    if not _HAS_WEASYPRINT:
        return html_content.encode('utf-8'), 'html'

    pdf_bytes = HTML(string=html_content, base_url=current_app.root_path).write_pdf()
    return pdf_bytes, 'pdf'


def generate_challan_pdf(invoice):
    """Generate combined PDF (4 challan copies) for a Delivery Challan."""
    from app.models import CompanySettings
    settings = CompanySettings.query.first()
    copies = [
        'Original for Recipient',
        'Duplicate for Transporter',
        'Triplicate for Supplier',
        'Office Copy',
    ]
    html_content = render_template(
        'challan/pdf_template.html',
        invoice=invoice,
        settings=settings,
        copies=copies,
    )
    if not _HAS_WEASYPRINT:
        return html_content.encode('utf-8'), 'html'

    pdf_bytes = HTML(string=html_content, base_url=current_app.root_path).write_pdf()
    return pdf_bytes, 'pdf'


def generate_combined_pdf(invoice):
    """Generate 7-page combined PDF (3 invoice + 4 challan)."""
    from app.models import CompanySettings
    settings = CompanySettings.query.first()
    hsn_breakup = get_hsn_breakup(
        [item.to_dict() for item in invoice.items],
        is_igst=invoice.is_igst
    )
    invoice_copies = [
        'Original for Recipient',
        'Duplicate for Transporter',
        'Triplicate for Supplier',
    ]
    challan_copies = [
        'Original for Recipient',
        'Duplicate for Transporter',
        'Triplicate for Supplier',
        'Office Copy',
    ]
    html_content = render_template(
        'combined_pdf_template.html',
        invoice=invoice,
        settings=settings,
        hsn_breakup=hsn_breakup,
        invoice_copies=invoice_copies,
        challan_copies=challan_copies,
    )
    if not _HAS_WEASYPRINT:
        return html_content.encode('utf-8'), 'html'

    pdf_bytes = HTML(string=html_content, base_url=current_app.root_path).write_pdf()
    return pdf_bytes, 'pdf'
