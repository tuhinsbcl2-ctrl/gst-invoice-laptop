"""
Reports & exports routes.
"""
import os
import shutil
import zipfile
from datetime import datetime, date
from flask import (Blueprint, render_template, request, send_file,
                   current_app, flash, redirect, url_for)
from app import db
from app.models import Invoice, Expense, Customer, Product, PurchaseVoucher, AccountHead
from app.services.excel_export import export_invoices_excel, export_invoices_csv
from app.services.tally_export import export_to_tally_xml
from sqlalchemy import func

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
def dashboard():
    # Summary stats
    invoices = Invoice.query.all()
    total_revenue = sum(i.grand_total for i in invoices)
    total_cgst = sum(i.cgst_total for i in invoices)
    total_sgst = sum(i.sgst_total for i in invoices)
    total_igst = sum(i.igst_total for i in invoices)

    unpaid = [i for i in invoices if i.payment_status in ('Unpaid', 'Partial')]
    outstanding = sum(i.grand_total for i in unpaid)

    expenses = Expense.query.all()
    total_expenses = sum(e.amount for e in expenses)

    # Monthly chart data (last 6 months)
    monthly = db.session.query(
        func.strftime('%Y-%m', Invoice.date).label('month'),
        func.sum(Invoice.grand_total).label('total')
    ).group_by('month').order_by('month').limit(12).all()
    chart_labels = [r.month for r in monthly]
    chart_data = [float(r.total or 0) for r in monthly]

    return render_template('reports/dashboard.html',
                           total_revenue=total_revenue,
                           total_cgst=total_cgst,
                           total_sgst=total_sgst,
                           total_igst=total_igst,
                           outstanding=outstanding,
                           total_expenses=total_expenses,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           invoices=invoices)


@reports_bp.route('/export/excel')
def export_excel():
    invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    data, ext = export_invoices_excel(invoices)
    from io import BytesIO
    return send_file(BytesIO(data),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True,
                     download_name=f'invoices_{date.today()}.{ext}')


@reports_bp.route('/export/csv')
def export_csv():
    invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    data, ext = export_invoices_csv(invoices)
    from io import BytesIO
    return send_file(BytesIO(data), mimetype='text/csv',
                     as_attachment=True,
                     download_name=f'invoices_{date.today()}.csv')


@reports_bp.route('/export/tally')
def export_tally():
    invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    data = export_to_tally_xml(invoices)
    from io import BytesIO
    return send_file(BytesIO(data), mimetype='application/xml',
                     as_attachment=True,
                     download_name=f'tally_export_{date.today()}.xml')


@reports_bp.route('/backup')
def backup():
    """Create a timestamped backup ZIP of the data folder."""
    backups_dir = current_app.config['BACKUPS_DIR']
    db_path = current_app.config['DATABASE_PATH']
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f'backup_{ts}.zip'
    zip_path = os.path.join(backups_dir, zip_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(db_path):
            zf.write(db_path, 'gst_billing.db')

    # Copy to Google Drive folder if configured
    from app.models import CompanySettings
    settings = CompanySettings.query.first()
    gdrive_folder = settings.gdrive_backup_folder if settings else None
    if gdrive_folder and os.path.isdir(gdrive_folder):
        try:
            shutil.copy2(zip_path, os.path.join(gdrive_folder, zip_name))
            flash(f'Backup created: {zip_name} (also copied to Google Drive folder)', 'success')
        except Exception as e:
            flash(f'Backup created: {zip_name} (GDrive copy failed: {e})', 'warning')
    else:
        flash(f'Backup created: {zip_name}', 'success')
    return send_file(zip_path, as_attachment=True, download_name=zip_name)


@reports_bp.route('/restore', methods=['GET', 'POST'])
def restore():
    """Restore the database from a backup ZIP."""
    if request.method == 'POST':
        f = request.files.get('backup_file')
        if not f or not f.filename.endswith('.zip'):
            flash('Please upload a valid .zip backup file.', 'danger')
            return redirect(url_for('reports.restore'))
        db_path = current_app.config['DATABASE_PATH']
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            f.save(tmp.name)
            with zipfile.ZipFile(tmp.name, 'r') as zf:
                if 'gst_billing.db' in zf.namelist():
                    zf.extract('gst_billing.db', os.path.dirname(db_path))
                    flash('Database restored successfully. Please restart the app.', 'success')
                else:
                    flash('Invalid backup file: gst_billing.db not found.', 'danger')
        return redirect(url_for('main.index'))
    return render_template('reports/restore.html')


def _current_fy_dates():
    """Return (date_from, date_to) for the current financial year."""
    today = date.today()
    if today.month >= 4:
        fy_start = date(today.year, 4, 1)
        fy_end = date(today.year + 1, 3, 31)
    else:
        fy_start = date(today.year - 1, 4, 1)
        fy_end = date(today.year, 3, 31)
    return fy_start, fy_end


def _fy_start_for_date(ref_date):
    """Return the financial year start date for a given reference date."""
    if ref_date.month >= 4:
        return date(ref_date.year, 4, 1)
    return date(ref_date.year - 1, 4, 1)


@reports_bp.route('/profit-loss')
def profit_loss():
    fy_start, fy_end = _current_fy_dates()
    date_from_str = request.args.get('date_from', fy_start.strftime('%Y-%m-%d'))
    date_to_str = request.args.get('date_to', fy_end.strftime('%Y-%m-%d'))

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
    except ValueError:
        date_from, date_to = fy_start, fy_end

    # Income: sum of invoice grand_total within date range
    invoices = Invoice.query.filter(Invoice.date >= date_from, Invoice.date <= date_to).all()
    total_income = sum(i.grand_total for i in invoices)

    # Direct Expenses: Expense records linked to 'Direct Expense' account type
    direct_expenses_list = Expense.query.join(
        AccountHead, Expense.account_head_id == AccountHead.id
    ).filter(
        Expense.date >= date_from, Expense.date <= date_to,
        AccountHead.account_type == 'Direct Expense'
    ).all()
    direct_exp_total = sum(e.amount for e in direct_expenses_list)

    # Add Regular purchase vouchers cost (subtotal = goods cost)
    regular_pvs = PurchaseVoucher.query.filter(
        PurchaseVoucher.date >= date_from,
        PurchaseVoucher.date <= date_to,
        PurchaseVoucher.voucher_type == 'Regular'
    ).all()
    purchase_cost = sum(v.subtotal for v in regular_pvs)

    direct_exp_total += purchase_cost
    gross_profit = total_income - direct_exp_total

    # Indirect Expenses: Expense records linked to 'Indirect Expense' account type
    indirect_expenses_list = Expense.query.join(
        AccountHead, Expense.account_head_id == AccountHead.id
    ).filter(
        Expense.date >= date_from, Expense.date <= date_to,
        AccountHead.account_type == 'Indirect Expense'
    ).all()
    indirect_exp_total = sum(e.amount for e in indirect_expenses_list)

    # Also include Expense-type purchase vouchers as indirect expense
    expense_pvs = PurchaseVoucher.query.filter(
        PurchaseVoucher.date >= date_from,
        PurchaseVoucher.date <= date_to,
        PurchaseVoucher.voucher_type == 'Expense'
    ).all()
    indirect_exp_total += sum(v.grand_total for v in expense_pvs)

    net_profit = gross_profit - indirect_exp_total

    return render_template('reports/profit_loss.html',
                           date_from=date_from, date_to=date_to,
                           total_income=total_income,
                           invoices=invoices,
                           direct_exp_total=direct_exp_total,
                           direct_expenses_list=direct_expenses_list,
                           purchase_cost=purchase_cost,
                           regular_pvs=regular_pvs,
                           gross_profit=gross_profit,
                           indirect_exp_total=indirect_exp_total,
                           indirect_expenses_list=indirect_expenses_list,
                           expense_pvs=expense_pvs,
                           net_profit=net_profit)


@reports_bp.route('/balance-sheet')
def balance_sheet():
    today = date.today()
    as_on_str = request.args.get('as_on', today.strftime('%Y-%m-%d'))
    try:
        as_on = datetime.strptime(as_on_str, '%Y-%m-%d').date()
    except ValueError:
        as_on = today

    # P&L for retained earnings — from start of FY to as_on date
    fy_start = _fy_start_for_date(as_on)

    invoices_ytd = Invoice.query.filter(Invoice.date >= fy_start, Invoice.date <= as_on).all()
    income_ytd = sum(i.grand_total for i in invoices_ytd)

    all_exp_ytd = Expense.query.filter(Expense.date >= fy_start, Expense.date <= as_on).all()
    expenses_ytd = sum(e.amount for e in all_exp_ytd)

    pv_ytd = PurchaseVoucher.query.filter(
        PurchaseVoucher.date >= fy_start,
        PurchaseVoucher.date <= as_on
    ).all()
    pv_cost_ytd = sum(v.grand_total for v in pv_ytd)
    net_profit_ytd = income_ytd - expenses_ytd - pv_cost_ytd

    # Fixed Assets: sum of Fixed Asset purchase vouchers up to as_on
    fixed_asset_pvs = PurchaseVoucher.query.filter(
        PurchaseVoucher.date <= as_on,
        PurchaseVoucher.voucher_type == 'Fixed Asset'
    ).all()
    fixed_assets_value = sum(v.grand_total for v in fixed_asset_pvs)

    # Current Assets
    unpaid_invoices = Invoice.query.filter(
        Invoice.date <= as_on,
        Invoice.payment_status.in_(['Unpaid', 'Partial'])
    ).all()
    sundry_debtors = sum(i.grand_total for i in unpaid_invoices)
    stock_value = sum(p.stock_quantity * p.default_unit_price for p in Product.query.all())

    # Current Liabilities
    unpaid_pvs = PurchaseVoucher.query.filter(
        PurchaseVoucher.date <= as_on,
        PurchaseVoucher.payment_status.in_(['Unpaid', 'Partial'])
    ).all()
    sundry_creditors = sum(v.grand_total for v in unpaid_pvs)

    # GST payable = sum of GST collected on invoices - GST paid on purchases
    gst_on_sales = sum(i.cgst_total + i.sgst_total + i.igst_total
                       for i in Invoice.query.filter(Invoice.date <= as_on).all())
    gst_on_purchases = sum(v.cgst_total + v.sgst_total + v.igst_total
                           for v in PurchaseVoucher.query.filter(PurchaseVoucher.date <= as_on).all())
    gst_payable = max(0, gst_on_sales - gst_on_purchases)

    total_assets = fixed_assets_value + sundry_debtors + stock_value
    total_liabilities = sundry_creditors + gst_payable + net_profit_ytd  # net profit goes to capital

    return render_template('reports/balance_sheet.html',
                           as_on=as_on,
                           fixed_assets_value=fixed_assets_value,
                           fixed_asset_pvs=fixed_asset_pvs,
                           sundry_debtors=sundry_debtors,
                           unpaid_invoices=unpaid_invoices,
                           stock_value=stock_value,
                           total_assets=total_assets,
                           sundry_creditors=sundry_creditors,
                           unpaid_pvs=unpaid_pvs,
                           gst_payable=gst_payable,
                           net_profit_ytd=net_profit_ytd,
                           total_liabilities=total_liabilities)


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _current_fy_dates():
    """Return (fy_start, fy_end) for the current Indian financial year."""
    today = date.today()
    if today.month >= 4:
        fy_start = date(today.year, 4, 1)
        fy_end = date(today.year + 1, 3, 31)
    else:
        fy_start = date(today.year - 1, 4, 1)
        fy_end = date(today.year, 3, 31)
    return fy_start, fy_end


# ---------------------------------------------------------------------------
# GSTR-1 Report
# ---------------------------------------------------------------------------

@reports_bp.route('/gstr1')
def gstr1():
    """GSTR-1: Monthly sales summary for GST filing."""
    today = date.today()
    # Default to current month
    month_str = request.args.get('month', today.strftime('%Y-%m'))
    date_from_str = request.args.get('date_from', '')
    date_to_str = request.args.get('date_to', '')

    try:
        if date_from_str and date_to_str:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
        else:
            parts = month_str.split('-')
            year, month = int(parts[0]), int(parts[1])
            from calendar import monthrange
            _, last_day = monthrange(year, month)
            date_from = date(year, month, 1)
            date_to = date(year, month, last_day)
    except (ValueError, IndexError):
        date_from = date(today.year, today.month, 1)
        date_to = today

    invoices = Invoice.query.filter(
        Invoice.date >= date_from,
        Invoice.date <= date_to
    ).order_by(Invoice.date).all()

    # Classify B2B (has GSTIN) vs B2C
    b2b_invoices = [i for i in invoices if i.buyer_gstin]
    b2c_invoices = [i for i in invoices if not i.buyer_gstin]

    def _sum(inv_list):
        return {
            'taxable': sum(i.subtotal for i in inv_list),
            'cgst': sum(i.cgst_total for i in inv_list),
            'sgst': sum(i.sgst_total for i in inv_list),
            'igst': sum(i.igst_total for i in inv_list),
            'total': sum(i.grand_total for i in inv_list),
        }

    b2b_totals = _sum(b2b_invoices)
    b2c_totals = _sum(b2c_invoices)
    all_totals = _sum(invoices)

    # Export to CSV
    if request.args.get('export') == 'csv':
        import csv
        from io import StringIO, BytesIO
        si = StringIO()
        writer = csv.writer(si)
        writer.writerow([
            'Invoice No', 'Date', 'Buyer Name', 'Buyer GSTIN',
            'Taxable', 'CGST', 'SGST', 'IGST', 'Grand Total', 'Type'
        ])
        for inv in invoices:
            writer.writerow([
                inv.invoice_no,
                inv.date.strftime('%d-%m-%Y'),
                inv.buyer_name,
                inv.buyer_gstin or '',
                f'{inv.subtotal:.2f}',
                f'{inv.cgst_total:.2f}',
                f'{inv.sgst_total:.2f}',
                f'{inv.igst_total:.2f}',
                f'{inv.grand_total:.2f}',
                'B2B' if inv.buyer_gstin else 'B2C',
            ])
        output = BytesIO(si.getvalue().encode('utf-8-sig'))
        return send_file(output, mimetype='text/csv', as_attachment=True,
                         download_name=f'GSTR1_{date_from}_{date_to}.csv')

    return render_template('reports/gstr1.html',
                           date_from=date_from, date_to=date_to,
                           month_str=month_str,
                           invoices=invoices,
                           b2b_invoices=b2b_invoices,
                           b2c_invoices=b2c_invoices,
                           b2b_totals=b2b_totals,
                           b2c_totals=b2c_totals,
                           all_totals=all_totals)


# ---------------------------------------------------------------------------
# GSTR-2B Reconciliation
# ---------------------------------------------------------------------------

@reports_bp.route('/gstr2b', methods=['GET', 'POST'])
def gstr2b():
    """GSTR-2B: Upload JSON and reconcile against purchase vouchers."""
    from app.models import PurchaseVoucher, Supplier

    reconciled = []
    unmatched_portal = []
    unmatched_local = []
    error_msg = None
    portal_records = []

    if request.method == 'POST':
        f = request.files.get('gstr2b_file')
        if not f or not f.filename.lower().endswith('.json'):
            flash('Please upload a valid GSTR-2B JSON file.', 'danger')
            return redirect(url_for('reports.gstr2b'))

        import json as json_mod
        try:
            raw = f.read().decode('utf-8')
            data = json_mod.loads(raw)
        except Exception as e:
            error_msg = f'Could not parse JSON: {e}'
            return render_template('reports/gstr2b.html',
                                   reconciled=[], unmatched_portal=[],
                                   unmatched_local=[], error_msg=error_msg)

        # Extract invoice records from GSTR-2B JSON
        # Standard GSTR-2B structure: data.docdata.b2b[].inv[]
        portal_records = _extract_gstr2b_records(data)

        # Load purchase vouchers from DB (current FY)
        fy_start, fy_end = _current_fy_dates()
        pvs = PurchaseVoucher.query.filter(
            PurchaseVoucher.date >= fy_start,
            PurchaseVoucher.date <= fy_end,
        ).all()

        # Build lookup: (gstin.upper(), inv_no.upper()) → PV
        pv_lookup = {}
        for pv in pvs:
            key = (
                (pv.supplier_gstin or '').strip().upper(),
                (pv.invoice_no or '').strip().upper(),
            )
            if key[0] or key[1]:
                pv_lookup[key] = pv

        matched_pv_ids = set()

        for rec in portal_records:
            gstin = rec.get('gstin', '').strip().upper()
            inv_no = rec.get('inum', '').strip().upper()
            key = (gstin, inv_no)
            pv = pv_lookup.get(key)
            if pv:
                matched_pv_ids.add(pv.id)
                # Check amount mismatch (tolerance ₹1)
                portal_val = float(rec.get('val', 0) or 0)
                local_val = pv.grand_total
                mismatch = abs(portal_val - local_val) > 1.0
                reconciled.append({
                    'portal': rec,
                    'local': pv,
                    'mismatch': mismatch,
                })
            else:
                unmatched_portal.append(rec)

        for pv in pvs:
            if pv.id not in matched_pv_ids and pv.supplier_gstin:
                unmatched_local.append(pv)

    return render_template('reports/gstr2b.html',
                           reconciled=reconciled,
                           unmatched_portal=unmatched_portal,
                           unmatched_local=unmatched_local,
                           error_msg=error_msg)


def _extract_gstr2b_records(data):
    """Extract a flat list of invoice dicts from GSTR-2B JSON structure."""
    records = []
    try:
        # Try standard GSTN structure: data.docdata.b2b[].inv[]
        doc_data = data.get('data', data)
        b2b_list = (doc_data.get('docdata', {}).get('b2b', [])
                    or doc_data.get('b2b', [])
                    or [])
        for supplier in b2b_list:
            gstin = supplier.get('ctin', '') or supplier.get('gstin', '')
            for inv in supplier.get('inv', []):
                inv['gstin'] = gstin
                records.append(inv)
    except Exception:
        pass
    return records
