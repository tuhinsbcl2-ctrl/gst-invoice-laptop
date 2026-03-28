"""
GST Calculation Logic.
- CGST + SGST for intra-state (buyer state == seller state 19)
- IGST for inter-state
"""


def calculate_gst(amount, gst_rate, is_igst=False):
    """Return dict with cgst, sgst, igst amounts."""
    if is_igst:
        igst = round(amount * gst_rate / 100, 2)
        return {'cgst_rate': 0, 'cgst_amount': 0,
                'sgst_rate': 0, 'sgst_amount': 0,
                'igst_rate': gst_rate, 'igst_amount': igst}
    else:
        half_rate = gst_rate / 2
        cgst = round(amount * half_rate / 100, 2)
        sgst = round(amount * half_rate / 100, 2)
        return {'cgst_rate': half_rate, 'cgst_amount': cgst,
                'sgst_rate': half_rate, 'sgst_amount': sgst,
                'igst_rate': 0, 'igst_amount': 0}


def is_igst_applicable(seller_state_code, buyer_state_code):
    """Return True if IGST should apply (inter-state supply)."""
    return str(seller_state_code).strip() != str(buyer_state_code).strip()


def calculate_invoice_totals(items, is_igst=False):
    """
    Calculate totals for an invoice given a list of item dicts.
    Each item dict should have: quantity, unit_price, gst_rate.
    Returns updated items list + totals dict.
    """
    subtotal = 0.0
    cgst_total = 0.0
    sgst_total = 0.0
    igst_total = 0.0

    processed_items = []
    for i, item in enumerate(items):
        qty = float(item.get('quantity', 0))
        price = float(item.get('unit_price', 0))
        gst_rate = float(item.get('gst_rate', 0))
        amount = round(qty * price, 2)
        gst = calculate_gst(amount, gst_rate, is_igst)

        subtotal += amount
        cgst_total += gst['cgst_amount']
        sgst_total += gst['sgst_amount']
        igst_total += gst['igst_amount']

        processed_items.append({
            **item,
            'sl_no': i + 1,
            'amount': amount,
            **gst,
        })

    subtotal = round(subtotal, 2)
    cgst_total = round(cgst_total, 2)
    sgst_total = round(sgst_total, 2)
    igst_total = round(igst_total, 2)

    total_before_round = subtotal + cgst_total + sgst_total + igst_total
    grand_total_raw = round(total_before_round)
    round_off = round(grand_total_raw - total_before_round, 2)
    grand_total = grand_total_raw

    return processed_items, {
        'subtotal': subtotal,
        'cgst_total': cgst_total,
        'sgst_total': sgst_total,
        'igst_total': igst_total,
        'round_off': round_off,
        'grand_total': grand_total,
    }


def get_hsn_breakup(items, is_igst=False):
    """
    Build HSN-wise tax breakup table from processed items.
    Returns list of dicts with HSN summary.
    """
    hsn_map = {}
    for item in items:
        hsn = item.get('hsn_code', '')
        gst_rate = float(item.get('gst_rate', 0))
        amount = float(item.get('amount', 0))
        key = (hsn, gst_rate)
        if key not in hsn_map:
            hsn_map[key] = {
                'hsn_code': hsn,
                'gst_rate': gst_rate,
                'taxable_value': 0.0,
                'cgst_rate': 0.0,
                'cgst_amount': 0.0,
                'sgst_rate': 0.0,
                'sgst_amount': 0.0,
                'igst_rate': 0.0,
                'igst_amount': 0.0,
                'total_tax': 0.0,
            }
        hsn_map[key]['taxable_value'] += amount
        hsn_map[key]['cgst_amount'] += float(item.get('cgst_amount', 0))
        hsn_map[key]['sgst_amount'] += float(item.get('sgst_amount', 0))
        hsn_map[key]['igst_amount'] += float(item.get('igst_amount', 0))
        if is_igst:
            hsn_map[key]['igst_rate'] = gst_rate
        else:
            hsn_map[key]['cgst_rate'] = gst_rate / 2
            hsn_map[key]['sgst_rate'] = gst_rate / 2

    result = []
    for row in hsn_map.values():
        row['taxable_value'] = round(row['taxable_value'], 2)
        row['cgst_amount'] = round(row['cgst_amount'], 2)
        row['sgst_amount'] = round(row['sgst_amount'], 2)
        row['igst_amount'] = round(row['igst_amount'], 2)
        row['total_tax'] = round(
            row['cgst_amount'] + row['sgst_amount'] + row['igst_amount'], 2)
        result.append(row)
    return result
