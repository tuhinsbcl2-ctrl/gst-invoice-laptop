"""
Shared helper utilities for form data parsing across routes.
"""


def safe_list_get(lst, index, default=''):
    """Safely get an element from a list by index, returning default if out of range."""
    return lst[index] if index < len(lst) else default


def safe_int(value, default=None):
    """Parse an int from a string, returning default if invalid or empty."""
    s = str(value).strip() if value is not None else ''
    return int(s) if s.isdigit() else default


def safe_float(value, default=0.0):
    """Parse a float from a string/number, returning default on failure."""
    try:
        return float(value) if value not in (None, '') else default
    except (ValueError, TypeError):
        return default


def parse_voucher_items(form, is_igst, with_account_head=False):
    """
    Parse line-item fields from a POST form (purchase voucher or return voucher).

    Expects form fields:
        product_id[], description[], hsn_code[], gst_rate[], quantity[],
        unit[], unit_price[]
    Optionally:
        item_account_head_id[]  (when with_account_head=True)

    Returns:
        (items: list[dict], subtotal, cgst_total, sgst_total, igst_total)
    """
    product_ids = form.getlist('product_id[]')
    descriptions = form.getlist('description[]')
    hsn_codes = form.getlist('hsn_code[]')
    gst_rates_raw = form.getlist('gst_rate[]')
    quantities_raw = form.getlist('quantity[]')
    units = form.getlist('unit[]')
    unit_prices_raw = form.getlist('unit_price[]')
    account_heads_raw = form.getlist('item_account_head_id[]') if with_account_head else []

    items = []
    subtotal = cgst_total = sgst_total = igst_total = 0.0

    for i, desc in enumerate(descriptions):
        if not desc.strip():
            continue

        qty = safe_float(safe_list_get(quantities_raw, i))
        price = safe_float(safe_list_get(unit_prices_raw, i))
        gst_rate = safe_float(safe_list_get(gst_rates_raw, i))
        amount = qty * price
        subtotal += amount

        cgst_amt = sgst_amt = igst_amt = 0.0
        if is_igst:
            igst_amt = round(amount * gst_rate / 100, 2)
            igst_total += igst_amt
        else:
            cgst_amt = round(amount * gst_rate / 200, 2)
            sgst_amt = cgst_amt
            cgst_total += cgst_amt
            sgst_total += sgst_amt

        pid = safe_int(safe_list_get(product_ids, i))
        item_ah_id = safe_int(safe_list_get(account_heads_raw, i)) if with_account_head else None

        item = dict(
            sl_no=len(items) + 1,
            product_id=pid,
            description=desc.strip(),
            hsn_code=safe_list_get(hsn_codes, i),
            gst_rate=gst_rate,
            quantity=qty,
            unit=safe_list_get(units, i, 'Pcs'),
            unit_price=price,
            amount=amount,
            cgst_amount=cgst_amt,
            sgst_amount=sgst_amt,
            igst_amount=igst_amt,
        )
        if with_account_head:
            item['account_head_id'] = item_ah_id

        items.append(item)

    return items, subtotal, cgst_total, sgst_total, igst_total
