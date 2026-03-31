"""
Chart of Accounts management routes.
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash)
from app import db
from app.models import AccountHead

accounts_bp = Blueprint('accounts', __name__)

ACCOUNT_TYPES = [
    'Direct Income',
    'Indirect Income',
    'Direct Expense',
    'Indirect Expense',
    'Fixed Assets',
    'Current Assets',
    'Current Liabilities',
    'Capital Account',
    'Bank Account',
    'Cash Account',
]


@accounts_bp.route('/')
def list_accounts():
    accounts = AccountHead.query.order_by(AccountHead.account_type, AccountHead.name).all()
    grouped = {}
    for acc in accounts:
        grouped.setdefault(acc.account_type, []).append(acc)
    return render_template('accounts/list.html', grouped=grouped, account_types=ACCOUNT_TYPES)


@accounts_bp.route('/create', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        data = request.form
        parent_id = data.get('parent_id') or None
        if parent_id:
            parent_id = int(parent_id)
        acc = AccountHead(
            name=data.get('name', ''),
            account_type=data.get('account_type', ''),
            parent_id=parent_id,
            description=data.get('description', ''),
            is_default=False,
        )
        db.session.add(acc)
        db.session.commit()
        flash(f'Account head "{acc.name}" created.', 'success')
        return redirect(url_for('accounts.list_accounts'))
    all_accounts = AccountHead.query.order_by(AccountHead.name).all()
    return render_template('accounts/form.html',
                           account_types=ACCOUNT_TYPES,
                           all_accounts=all_accounts)


@accounts_bp.route('/<int:aid>/edit', methods=['GET', 'POST'])
def edit_account(aid):
    acc = AccountHead.query.get_or_404(aid)
    if request.method == 'POST':
        data = request.form
        parent_id = data.get('parent_id') or None
        if parent_id:
            parent_id = int(parent_id)
        acc.name = data.get('name', '')
        acc.account_type = data.get('account_type', '')
        acc.parent_id = parent_id
        acc.description = data.get('description', '')
        db.session.commit()
        flash('Account head updated.', 'success')
        return redirect(url_for('accounts.list_accounts'))
    all_accounts = AccountHead.query.filter(AccountHead.id != aid).order_by(AccountHead.name).all()
    return render_template('accounts/form.html', account=acc, edit_mode=True,
                           account_types=ACCOUNT_TYPES, all_accounts=all_accounts)


@accounts_bp.route('/<int:aid>/delete', methods=['POST'])
def delete_account(aid):
    acc = AccountHead.query.get_or_404(aid)
    if acc.is_default:
        flash('Cannot delete a default system account.', 'danger')
        return redirect(url_for('accounts.list_accounts'))
    # Check for references in expenses, purchase vouchers, bank transactions
    from app.models import Expense, PurchaseVoucher, PurchaseVoucherItem, BankTransaction
    if (Expense.query.filter_by(account_head_id=aid).first() or
            PurchaseVoucher.query.filter_by(account_head_id=aid).first() or
            PurchaseVoucherItem.query.filter_by(account_head_id=aid).first() or
            BankTransaction.query.filter_by(account_head_id=aid).first()):
        flash('Cannot delete: account head is referenced by existing transactions.', 'danger')
        return redirect(url_for('accounts.list_accounts'))
    db.session.delete(acc)
    db.session.commit()
    flash('Account head deleted.', 'info')
    return redirect(url_for('accounts.list_accounts'))
