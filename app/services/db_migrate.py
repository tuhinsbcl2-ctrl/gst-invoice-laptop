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


_KNOWN_TABLES = frozenset([
    'expenses', 'purchase_vouchers', 'purchase_voucher_items',
    'bank_transactions', 'invoices', 'account_heads',
    'invoice_sequence', 'customers', 'suppliers', 'products',
    'invoice_items', 'company_settings',
])

_KNOWN_COLUMNS = frozenset([
    'account_head_id', 'is_reconciled', 'linked_invoice_id', 'linked_purchase_id',
])


def _get_table_columns(conn, table_name):
    """Return a set of column names for the given table (or empty set if table missing)."""
    if table_name not in _KNOWN_TABLES:
        return set()
    try:
        rows = conn.execute(text(f'PRAGMA table_info("{table_name}")')).fetchall()
        return {row[1] for row in rows}
    except Exception:
        return set()


def _table_exists(conn, table_name):
    """Return True if the table exists in the database."""
    if table_name not in _KNOWN_TABLES:
        return False
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name}
    ).fetchone()
    return row is not None


def migrate_sqlite_schema(app):
    """
    Run lightweight migrations for SQLite databases.

    - Creates missing tables via db.create_all().
    - Adds missing columns (ALTER TABLE ... ADD COLUMN) for existing tables.
    - Seeds default AccountHead records if none exist.
    - Ensures InvoiceSequence has a 'PV' row for the current FY.
    """
    from app import db

    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'sqlite' not in db_uri:
        return

    with app.app_context():
        # First run create_all so all new tables get created
        db.create_all()

        with db.engine.connect() as conn:
            with conn.begin():
                _add_missing_columns(conn)

        _seed_account_heads(db)
        _ensure_pv_sequence(db)


def _add_missing_columns(conn):
    """Add any missing columns to existing tables."""
    # (table_name, column_name, column_definition)
    required_columns = [
        ('expenses', 'account_head_id', 'INTEGER REFERENCES account_heads(id)'),
        ('purchase_vouchers', 'account_head_id', 'INTEGER REFERENCES account_heads(id)'),
        ('purchase_voucher_items', 'account_head_id', 'INTEGER REFERENCES account_heads(id)'),
        ('bank_transactions', 'account_head_id', 'INTEGER REFERENCES account_heads(id)'),
        ('bank_transactions', 'is_reconciled', 'BOOLEAN DEFAULT 0'),
        ('bank_transactions', 'linked_invoice_id', 'INTEGER REFERENCES invoices(id)'),
        ('bank_transactions', 'linked_purchase_id', 'INTEGER REFERENCES purchase_vouchers(id)'),
    ]

    for table, column, col_def in required_columns:
        if table not in _KNOWN_TABLES or column not in _KNOWN_COLUMNS:
            continue
        if not _table_exists(conn, table):
            continue
        existing = _get_table_columns(conn, table)
        if column not in existing:
            try:
                conn.execute(
                    text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_def}')
                )
            except Exception:
                pass


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


def _ensure_pv_sequence(db):
    """Ensure the InvoiceSequence table has a row for prefix 'PV' in the current FY."""
    from app.models import InvoiceSequence
    from app.services.invoice_numbering import get_financial_year
    try:
        fy = get_financial_year()
        existing = InvoiceSequence.query.filter_by(prefix='PV', financial_year=fy).first()
        if not existing:
            db.session.add(InvoiceSequence(prefix='PV', financial_year=fy, last_serial=0))
            db.session.commit()
    except Exception:
        db.session.rollback()
