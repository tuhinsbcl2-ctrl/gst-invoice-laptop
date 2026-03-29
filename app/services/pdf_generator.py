"""
PDF generation for Tax Invoice and Delivery Challan using xhtml2pdf (pisa).
Renders HTML templates to PDF bytes.  xhtml2pdf is a pure-Python library
that works on Windows without any native dependencies (no GTK/Cairo needed).
"""
import io
import logging
from flask import render_template
from app.services.gst_calculator import get_hsn_breakup

logger = logging.getLogger(__name__)

try:
    from xhtml2pdf import pisa
    _HAS_PDF_ENGINE = True
except Exception:
    _HAS_PDF_ENGINE = False


def _html_to_pdf(html_content):
    """Convert an HTML string to PDF bytes using xhtml2pdf."""
    result_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html_content), dest=result_buffer)
    if pisa_status.err:
        logger.error("xhtml2pdf PDF generation failed with %d error(s)", pisa_status.err)
        return None
    return result_buffer.getvalue()


def generate_invoice_pdf(invoice):
    """Generate combined PDF (4 invoice copies) for a Tax Invoice."""
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
        'Office Copy',
    ]
    html_content = render_template(
        'invoice/pdf_template.html',
        invoice=invoice,
        settings=settings,
        hsn_breakup=hsn_breakup,
        copies=copies,
    )
    if not _HAS_PDF_ENGINE:
        return html_content.encode('utf-8'), 'html'

    pdf_bytes = _html_to_pdf(html_content)
    if pdf_bytes is None:
        return html_content.encode('utf-8'), 'html'
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
    if not _HAS_PDF_ENGINE:
        return html_content.encode('utf-8'), 'html'

    pdf_bytes = _html_to_pdf(html_content)
    if pdf_bytes is None:
        return html_content.encode('utf-8'), 'html'
    return pdf_bytes, 'pdf'


def generate_combined_pdf(invoice):
    """Generate 8-page combined PDF (4 invoice + 4 challan)."""
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
        'Office Copy',
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
    if not _HAS_PDF_ENGINE:
        return html_content.encode('utf-8'), 'html'

    pdf_bytes = _html_to_pdf(html_content)
    if pdf_bytes is None:
        return html_content.encode('utf-8'), 'html'
    return pdf_bytes, 'pdf'
