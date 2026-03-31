"""
Bank Statement import and management routes.
"""
import io
import csv
from datetime import datetime, date
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify)
from app import db
from app.models import BankTransaction, AccountHead, Invoice, PurchaseVoucher

bank_bp = Blueprint('bank', __name__)

# Keywords for auto-categorisation
AUTO_CATEGORISE_RULES = [
    (['INTEREST', 'INT CR', 'INT CREDIT'], 'Interest Received'),
    (['SALARY', 'WAGES', 'PAYROLL'], 'Salary Expense'),
    (['RENT'], 'Rent'),
    (['ELECTRICITY', 'POWER', 'BESCOM', 'CESC', 'WBSEDCL'], 'Electricity'),
    (['TELEPHONE', 'MOBILE', 'BROADBAND', 'INTERNET', 'AIRTEL', 'JIOFIBER', 'BSNL'], 'Telephone'),
    (['GST', 'TAX PAYMENT', 'GSTN', 'CBEC'], 'GST Payable'),
    (['NEFT', 'RTGS', 'IMPS'], 'Bank Transfer'),
    (['UPI'], 'UPI Payment'),
]

# Column name mappings for flexible CSV parsing
DATE_COLUMNS = ['date', 'txn date', 'transaction date', 'value date', 'posting date']
DESC_COLUMNS = ['description', 'narration', 'particulars', 'transaction remarks', 'details']
DEBIT_COLUMNS = ['debit', 'withdrawal', 'dr', 'debit amount', 'withdrawal amount']
CREDIT_COLUMNS = ['credit', 'deposit', 'cr', 'credit amount', 'deposit amount']
BALANCE_COLUMNS = ['balance', 'closing balance', 'available balance', 'running balance']
REF_COLUMNS = ['ref', 'reference', 'chq/ref no', 'chq no', 'transaction id', 'ref no']


def _find_column(headers, candidates):
    for h in headers:
        if h.strip().lower() in candidates:
            return h
    return None


def _parse_amount(val):
    if not val or str(val).strip() in ('', '-', 'Dr', 'Cr'):
        return 0.0
    val = str(val).replace(',', '').replace(' ', '').strip()
    if val.endswith('Dr') or val.endswith('CR'):
        val = val[:-2].strip()
    try:
        return float(val)
    except ValueError:
        return 0.0


def _auto_categorise(description):
    desc_upper = (description or '').upper()
    for keywords, category in AUTO_CATEGORISE_RULES:
        for kw in keywords:
            if kw in desc_upper:
                return category
    return 'Uncategorised'


@bank_bp.route('/')
def list_transactions():
    date_from_str = request.args.get('date_from', '')
    date_to_str = request.args.get('date_to', '')
    bank_filter = request.args.get('bank', '')
    category_filter = request.args.get('category', '')
    reconciled_filter = request.args.get('reconciled', '')

    q = BankTransaction.query
    if date_from_str:
        try:
            q = q.filter(BankTransaction.date >= datetime.strptime(date_from_str, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to_str:
        try:
            q = q.filter(BankTransaction.date <= datetime.strptime(date_to_str, '%Y-%m-%d').date())
        except ValueError:
            pass
    if bank_filter:
        q = q.filter(BankTransaction.bank_name.ilike(f'%{bank_filter}%'))
    if category_filter:
        q = q.filter(BankTransaction.category == category_filter)
    if reconciled_filter == '1':
        q = q.filter(BankTransaction.is_reconciled.is_(True))
    elif reconciled_filter == '0':
        q = q.filter(BankTransaction.is_reconciled.is_(False))

    transactions = q.order_by(BankTransaction.date.desc()).all()
    total_debit = sum(t.debit for t in transactions)
    total_credit = sum(t.credit for t in transactions)

    # Distinct categories for filter dropdown
    categories = [r[0] for r in db.session.query(BankTransaction.category).distinct()
                  if r[0]]
    banks = [r[0] for r in db.session.query(BankTransaction.bank_name).distinct()
             if r[0]]

    return render_template('bank/list.html',
                           transactions=transactions,
                           total_debit=total_debit,
                           total_credit=total_credit,
                           categories=categories,
                           banks=banks,
                           filters=dict(date_from=date_from_str, date_to=date_to_str,
                                        bank=bank_filter, category=category_filter,
                                        reconciled=reconciled_filter))


@bank_bp.route('/import', methods=['GET', 'POST'])
def import_bank():
    if request.method == 'POST':
        f = request.files.get('statement_file')
        bank_name = request.form.get('bank_name', '')
        if not f:
            flash('No file uploaded.', 'danger')
            return redirect(url_for('bank.import_bank'))

        filename = f.filename.lower()
        try:
            if filename.endswith('.csv'):
                content = f.read().decode('utf-8', errors='ignore')
                reader = csv.DictReader(io.StringIO(content))
                headers = reader.fieldnames or []
            elif filename.endswith(('.xlsx', '.xls')):
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(f.read()), data_only=True)
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    flash('Empty file.', 'danger')
                    return redirect(url_for('bank.import_bank'))
                headers = [str(h).strip() if h else '' for h in rows[0]]
                reader = [dict(zip(headers, [str(v).strip() if v is not None else '' for v in row]))
                          for row in rows[1:]]
            else:
                flash('Please upload a CSV or Excel (.xlsx) file.', 'danger')
                return redirect(url_for('bank.import_bank'))

            date_col = _find_column(headers, DATE_COLUMNS)
            desc_col = _find_column(headers, DESC_COLUMNS)
            debit_col = _find_column(headers, DEBIT_COLUMNS)
            credit_col = _find_column(headers, CREDIT_COLUMNS)
            balance_col = _find_column(headers, BALANCE_COLUMNS)
            ref_col = _find_column(headers, REF_COLUMNS)

            if not date_col:
                flash('Could not find a Date column in the file. Please check column headers.', 'danger')
                return redirect(url_for('bank.import_bank'))

            imported = 0
            skipped = 0
            for row in reader:
                date_val = row.get(date_col, '').strip()
                if not date_val or date_val.lower() in ('nan', '', 'none'):
                    skipped += 1
                    continue

                txn_date = None
                for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d-%b-%Y',
                            '%d/%m/%y', '%d-%m-%y'):
                    try:
                        txn_date = datetime.strptime(date_val, fmt).date()
                        break
                    except ValueError:
                        continue
                if not txn_date:
                    skipped += 1
                    continue

                description = row.get(desc_col, '') if desc_col else ''
                debit = _parse_amount(row.get(debit_col, '') if debit_col else '')
                credit = _parse_amount(row.get(credit_col, '') if credit_col else '')
                balance = _parse_amount(row.get(balance_col, '') if balance_col else '')
                ref_no = row.get(ref_col, '') if ref_col else ''

                category = _auto_categorise(description)

                txn = BankTransaction(
                    date=txn_date,
                    description=description,
                    reference_no=ref_no,
                    debit=debit,
                    credit=credit,
                    balance=balance,
                    bank_name=bank_name,
                    category=category,
                )
                db.session.add(txn)
                imported += 1

            db.session.commit()
            flash(f'Imported {imported} transactions. Skipped {skipped} rows.', 'success')
            return redirect(url_for('bank.list_transactions'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error parsing file: {e}', 'danger')
            return redirect(url_for('bank.import_bank'))

    return render_template('bank/import.html')


@bank_bp.route('/<int:tid>/categorise', methods=['GET', 'POST'])
def categorise_transaction(tid):
    txn = BankTransaction.query.get_or_404(tid)
    if request.method == 'POST':
        data = request.form
        txn.category = data.get('category', txn.category)
        account_head_id = data.get('account_head_id') or None
        txn.account_head_id = int(account_head_id) if account_head_id else None
        linked_invoice_id = data.get('linked_invoice_id') or None
        txn.linked_invoice_id = int(linked_invoice_id) if linked_invoice_id else None
        linked_purchase_id = data.get('linked_purchase_id') or None
        txn.linked_purchase_id = int(linked_purchase_id) if linked_purchase_id else None
        txn.is_reconciled = data.get('is_reconciled') == 'on'
        db.session.commit()
        flash('Transaction categorised.', 'success')
        return redirect(url_for('bank.list_transactions'))

    account_heads = AccountHead.query.order_by(AccountHead.account_type, AccountHead.name).all()
    invoices = Invoice.query.order_by(Invoice.date.desc()).limit(50).all()
    purchases = PurchaseVoucher.query.order_by(PurchaseVoucher.date.desc()).limit(50).all()
    return render_template('bank/categorise.html',
                           txn=txn,
                           account_heads=account_heads,
                           invoices=invoices,
                           purchases=purchases)


@bank_bp.route('/auto-categorise', methods=['POST'])
def auto_categorise_all():
    uncategorised = BankTransaction.query.filter(
        (BankTransaction.category.is_(None)) |
        (BankTransaction.category == 'Uncategorised')
    ).all()
    count = 0
    for txn in uncategorised:
        new_cat = _auto_categorise(txn.description)
        if new_cat != 'Uncategorised':
            txn.category = new_cat
            count += 1
        else:
            txn.category = 'Uncategorised'
    db.session.commit()
    flash(f'Auto-categorised {count} transactions.', 'success')
    return redirect(url_for('bank.list_transactions'))
