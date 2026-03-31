"""
Lightweight SQLite schema migration on startup.

Adds missing columns to existing tables without deleting data.
This handles the case where users have an older database and
new code adds columns via model changes.
"""
from sqlalchemy import text


DEFAULT_ACCOUNT_HEADS = [
    ('Sales Account', 'Direct Income'),
    ('Service Income', 'Indirect Income'),
    ('Other Income', 'Indirect Income'),
    ('Purchase Account', 'Direct Expense'),
    ('Direct Expenses', 'Direct Expense'),
    ('Office Expenses', 'Indirect Expense'),
    ('Salaries & Wages', 'Indirect Expense'),
    ('Rent', 'Indirect Expense'),
    ('Utilities', 'Indirect Expense'),
    ('Depreciation', 'Indirect Expense'),
    ('Furniture & Fixtures', 'Fixed Assets'),
    ('Computer & Equipment', 'Fixed Assets'),
    ('Machinery', 'Fixed Assets'),
    ('Cash in Hand', 'Cash Account'),
    ('Bank Account', 'Bank Account'),
    ('Sundry Debtors', 'Current Assets'),
    ('Sundry Creditors', 'Current Liabilities'),
    ('Capital Account', 'Capital Account'),
]


def _get_table_columns(conn, table_name):
    """Return a set of column names for the given table (or empty set if table missing)."""
    try:
        rows = conn.execute(text(f'PRAGMA table_info("{table_name}")')).fetchall()
        return {row[1] for row in rows}
    except Exception:
        return set()


def _table_exists(conn, table_name):
    """Return True if the table exists in the database."""
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name}
    ).fetchone()
    return row is not None


def _add_column_if_missing(conn, table, column, col_def):
    """Add a column to a table if it does not already exist."""
    if not _table_exists(conn, table):
        return
    existing = _get_table_columns(conn, table)
    if column not in existing:
        try:
            conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_def}'))
        except Exception:
            pass


def migrate_sqlite_schema(app):
    """
    Run lightweight migrations for SQLite databases.

    - Creates missing tables via db.create_all().
    - Adds missing columns (ALTER TABLE ... ADD COLUMN) for existing tables.
    - Seeds default AccountHead records if none exist.
    - Ensures InvoiceSequence has rows for PV / PR / SR prefixes in the current FY.
    """
    from app import db

    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'sqlite' not in db_uri:
        return

    with app.app_context():
        # Create all tables that don't exist yet (new models)
        db.create_all()

        with db.engine.connect() as conn:
            with conn.begin():
                _add_missing_columns(conn)

        # These helpers need an active app context – keep them inside
        _seed_account_heads(db)
        _ensure_sequences(db)


def _add_missing_columns(conn):
    """Add any missing columns to existing tables."""

    # company_settings – Google Drive backup folder
    _add_column_if_missing(conn, 'company_settings', 'gdrive_backup_folder', 'TEXT')

    # expenses – account head link
    _add_column_if_missing(conn, 'expenses', 'account_head_id',
                           'INTEGER REFERENCES account_heads(id)')

    # purchase_vouchers – account head link
    _add_column_if_missing(conn, 'purchase_vouchers', 'account_head_id',
                           'INTEGER REFERENCES account_heads(id)')

    # purchase_voucher_items – product link + account head
    _add_column_if_missing(conn, 'purchase_voucher_items', 'product_id',
                           'INTEGER REFERENCES products(id)')
    _add_column_if_missing(conn, 'purchase_voucher_items', 'account_head_id',
                           'INTEGER REFERENCES account_heads(id)')

    # bank_transactions – reconciliation & links
    _add_column_if_missing(conn, 'bank_transactions', 'account_head_id',
                           'INTEGER REFERENCES account_heads(id)')
    _add_column_if_missing(conn, 'bank_transactions', 'is_reconciled', 'BOOLEAN DEFAULT 0')
    _add_column_if_missing(conn, 'bank_transactions', 'linked_invoice_id',
                           'INTEGER REFERENCES invoices(id)')
    _add_column_if_missing(conn, 'bank_transactions', 'linked_purchase_id',
                           'INTEGER REFERENCES purchase_vouchers(id)')

    # invoices – ship-to details and way bill
    _add_column_if_missing(conn, 'invoices', 'ship_to_same', 'BOOLEAN DEFAULT 1')
    _add_column_if_missing(conn, 'invoices', 'ship_to_name', 'VARCHAR(200)')
    _add_column_if_missing(conn, 'invoices', 'ship_to_address', 'TEXT')
    _add_column_if_missing(conn, 'invoices', 'ship_to_state', 'VARCHAR(50)')
    _add_column_if_missing(conn, 'invoices', 'ship_to_gstin', 'VARCHAR(20)')
    _add_column_if_missing(conn, 'invoices', 'way_bill_no', 'VARCHAR(50)')


def _seed_account_heads(db):
    """Insert default account heads if the table is empty."""
    from app.models import AccountHead
    try:
        if AccountHead.query.count() == 0:
            for name, acct_type in DEFAULT_ACCOUNT_HEADS:
                db.session.add(AccountHead(
                    name=name,
                    account_type=acct_type,
                    is_default=True,
                ))
            db.session.commit()
    except Exception:
        db.session.rollback()


def _ensure_sequences(db):
    """Ensure InvoiceSequence rows exist for PV, PR, SR prefixes in the current FY."""
    from app.models import InvoiceSequence
    from app.services.invoice_numbering import get_financial_year
    try:
        fy = get_financial_year()
        for prefix in ('PV', 'PR', 'SR'):
            existing = InvoiceSequence.query.filter_by(
                prefix=prefix, financial_year=fy
            ).first()
            if not existing:
                db.session.add(InvoiceSequence(
                    prefix=prefix, financial_year=fy, last_serial=0
                ))
        db.session.commit()
    except Exception:
        db.session.rollback()
