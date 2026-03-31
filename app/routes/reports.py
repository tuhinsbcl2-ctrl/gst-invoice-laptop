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
    data_dir = current_app.config['BASE_DIR']
    db_path = current_app.config['DATABASE_PATH']
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f'backup_{ts}.zip'
    zip_path = os.path.join(backups_dir, zip_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(db_path):
            zf.write(db_path, 'gst_billing.db')
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
    direct_exp_q = Expense.query.join(AccountHead, Expense.account_head_id == AccountHead.id, isouter=True).filter(
        Expense.date >= date_from, Expense.date <= date_to
    )
    direct_expenses_list = [e for e in direct_exp_q.all()
                            if e.account_head and e.account_head.account_type == 'Direct Expense']
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
    all_expenses_in_range = Expense.query.filter(
        Expense.date >= date_from, Expense.date <= date_to
    ).all()
    indirect_expenses_list = [e for e in all_expenses_in_range
                              if e.account_head and e.account_head.account_type == 'Indirect Expense']
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
    if as_on.month >= 4:
        fy_start = date(as_on.year, 4, 1)
    else:
        fy_start = date(as_on.year - 1, 4, 1)

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
