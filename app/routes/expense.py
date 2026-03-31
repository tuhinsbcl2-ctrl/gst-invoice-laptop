"""
Expense tracking routes.
"""
from datetime import datetime, date
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash)
from app import db
from app.models import Expense, AccountHead

expense_bp = Blueprint('expense', __name__)


@expense_bp.route('/')
def list_expenses():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    total = sum(e.amount for e in expenses)
    return render_template('expense/list.html', expenses=expenses, total=total)


@expense_bp.route('/create', methods=['GET', 'POST'])
def create_expense():
    if request.method == 'POST':
        data = request.form
        exp_date_str = data.get('date', date.today().strftime('%Y-%m-%d'))
        exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
        account_head_id = data.get('account_head_id') or None
        if account_head_id:
            account_head_id = int(account_head_id)
        e = Expense(
            date=exp_date,
            description=data.get('description', ''),
            amount=float(data.get('amount', 0.0) or 0.0),
            mode=data.get('mode', 'Cash'),
            bank_name=data.get('bank_name', ''),
            category=data.get('category', ''),
            account_head_id=account_head_id,
        )
        db.session.add(e)
        db.session.commit()
        flash('Expense recorded.', 'success')
        return redirect(url_for('expense.list_expenses'))
    account_heads = AccountHead.query.filter(
        AccountHead.account_type.in_(['Direct Expense', 'Indirect Expense'])
    ).order_by(AccountHead.account_type, AccountHead.name).all()
    return render_template('expense/form.html',
                           today=date.today().strftime('%Y-%m-%d'),
                           account_heads=account_heads)


@expense_bp.route('/<int:eid>/edit', methods=['GET', 'POST'])
def edit_expense(eid):
    e = Expense.query.get_or_404(eid)
    if request.method == 'POST':
        data = request.form
        exp_date_str = data.get('date', date.today().strftime('%Y-%m-%d'))
        e.date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
        e.description = data.get('description', '')
        e.amount = float(data.get('amount', 0.0) or 0.0)
        e.mode = data.get('mode', 'Cash')
        e.bank_name = data.get('bank_name', '')
        e.category = data.get('category', '')
        account_head_id = data.get('account_head_id') or None
        e.account_head_id = int(account_head_id) if account_head_id else None
        db.session.commit()
        flash('Expense updated.', 'success')
        return redirect(url_for('expense.list_expenses'))
    account_heads = AccountHead.query.filter(
        AccountHead.account_type.in_(['Direct Expense', 'Indirect Expense'])
    ).order_by(AccountHead.account_type, AccountHead.name).all()
    return render_template('expense/form.html', expense=e, edit_mode=True,
                           account_heads=account_heads)


@expense_bp.route('/<int:eid>/delete', methods=['POST'])
def delete_expense(eid):
    e = Expense.query.get_or_404(eid)
    db.session.delete(e)
    db.session.commit()
    flash('Expense deleted.', 'info')
    return redirect(url_for('expense.list_expenses'))
