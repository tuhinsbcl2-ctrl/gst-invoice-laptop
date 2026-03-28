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
from app.models import Invoice, Expense, Customer, Product
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
