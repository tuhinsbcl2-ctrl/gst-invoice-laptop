"""
Auto-sequencing invoice numbering.
Format: PREFIX/SERIAL/YEAR  e.g. NE/008/25-26
"""
from datetime import date


def get_financial_year(ref_date=None):
    """Return financial year string like '25-26'."""
    if ref_date is None:
        ref_date = date.today()
    year = ref_date.year
    month = ref_date.month
    if month >= 4:
        return f"{str(year)[2:]}-{str(year + 1)[2:]}"
    else:
        return f"{str(year - 1)[2:]}-{str(year)[2:]}"


def get_next_invoice_number(prefix='NE', ref_date=None):
    """
    Fetch/increment the serial for the given prefix and current FY.
    Returns formatted invoice number string.
    """
    from app import db
    from app.models import InvoiceSequence

    fy = get_financial_year(ref_date)
    seq = InvoiceSequence.query.filter_by(prefix=prefix, financial_year=fy).first()
    if not seq:
        seq = InvoiceSequence(prefix=prefix, financial_year=fy, last_serial=0)
        db.session.add(seq)

    seq.last_serial += 1
    db.session.commit()

    serial_str = str(seq.last_serial).zfill(3)
    return f"{prefix}/{serial_str}/{fy}"


def peek_next_invoice_number(prefix='NE', ref_date=None):
    """Preview what the next invoice number will be (no increment)."""
    from app.models import InvoiceSequence

    fy = get_financial_year(ref_date)
    seq = InvoiceSequence.query.filter_by(prefix=prefix, financial_year=fy).first()
    next_serial = (seq.last_serial + 1) if seq else 1
    serial_str = str(next_serial).zfill(3)
    return f"{prefix}/{serial_str}/{fy}"
