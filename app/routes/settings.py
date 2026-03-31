"""
Company settings routes.
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash)
from app import db
from app.models import CompanySettings

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/', methods=['GET', 'POST'])
def index():
    settings = CompanySettings.query.first()
    if not settings:
        settings = CompanySettings()
        db.session.add(settings)

    if request.method == 'POST':
        data = request.form
        settings.company_name = data.get('company_name', '')
        settings.address = data.get('address', '')
        settings.gstin = data.get('gstin', '')
        settings.pan = data.get('pan', '')
        settings.udyam = data.get('udyam', '')
        settings.state_name = data.get('state_name', '')
        settings.state_code = data.get('state_code', '')
        settings.bank_name = data.get('bank_name', '')
        settings.bank_account = data.get('bank_account', '')
        settings.bank_ifsc = data.get('bank_ifsc', '')
        settings.bank_branch = data.get('bank_branch', '')
        settings.invoice_prefix = data.get('invoice_prefix', 'NE')
        settings.gdrive_backup_folder = data.get('gdrive_backup_folder', '').strip()
        db.session.commit()
        flash('Settings saved successfully.', 'success')
        return redirect(url_for('settings.index'))

    return render_template('settings.html', settings=settings)
