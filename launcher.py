"""
launcher.py — Entry point for the standalone Windows .exe build.

When the user double-clicks GSTBillingApp.exe this script:
  1. Resolves the correct base / bundle paths (frozen vs. normal Python)
  2. Ensures data/, exports/, backups/ directories exist next to the .exe
  3. Runs first-time database initialisation if gst_billing.db does not exist
  4. Starts the Flask development server in the current thread
  5. Opens the default browser to http://localhost:5000 after a short delay

Usage (normal Python, for testing):
    python launcher.py
"""

import os
import sys
import threading
import webbrowser

# ---------------------------------------------------------------------------
# Path resolution — must happen before any project imports so that config.py
# picks up the correct BASE_DIR / BUNDLE_DIR values.
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller-compiled executable.
    # sys._MEIPASS  → unpacked bundle (read-only, contains app code/templates/static)
    # sys.executable directory → next to the .exe (user-writable, data lives here)
    EXE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, '_MEIPASS', EXE_DIR)
    # Add the bundle dir to sys.path so our app modules are importable
    if BUNDLE_DIR not in sys.path:
        sys.path.insert(0, BUNDLE_DIR)
else:
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = EXE_DIR

# ---------------------------------------------------------------------------
# First-time database setup
# ---------------------------------------------------------------------------

def _first_run_setup():
    """Initialise the database and seed default data on first run."""
    db_path = os.path.join(EXE_DIR, 'data', 'gst_billing.db')
    if os.path.exists(db_path):
        return  # Already initialised — nothing to do

    print("  [INFO] First run detected — initialising database...")
    try:
        from app import create_app, db as _db
        from app.models import CompanySettings, InvoiceSequence, AccountHead

        _app = create_app()
        with _app.app_context():
            _db.create_all()

            if not CompanySettings.query.first():
                settings = CompanySettings(
                    company_name='NIBRITY ENTERPRISE (GOVT ORDER SUPPLIER)',
                    address='213, Kadarat, Sonarpur, Ward No 7, Rajpur Sonarpur, '
                            'P.S.: Narendrapur, South 24 Four Parganas, Kolkata: 700150',
                    gstin='19CDOPM2160E1ZH',
                    pan='CDOPM2160E',
                    udyam='UDYAM-WB-18-0133096',
                    state_name='West Bengal',
                    state_code='19',
                    bank_name='Punjab National Bank',
                    bank_account='1493202100001135',
                    bank_ifsc='PUNB0149320',
                    bank_branch='SONARGAON',
                    invoice_prefix='NE',
                )
                _db.session.add(settings)
                _db.session.commit()

            from app.services.invoice_numbering import get_financial_year
            fy = get_financial_year()
            if not InvoiceSequence.query.filter_by(prefix='NE', financial_year=fy).first():
                _db.session.add(InvoiceSequence(prefix='NE', financial_year=fy, last_serial=0))
                _db.session.commit()

            if not InvoiceSequence.query.filter_by(prefix='PV', financial_year=fy).first():
                _db.session.add(InvoiceSequence(prefix='PV', financial_year=fy, last_serial=0))
                _db.session.commit()

            # Seed default account heads
            if not AccountHead.query.filter_by(is_default=True).first():
                default_accounts = [
                    ('Sales', 'Direct Income'), ('Service Income', 'Direct Income'),
                    ('Interest Received', 'Indirect Income'), ('Other Income', 'Indirect Income'),
                    ('Purchases', 'Direct Expense'), ('Freight Inward', 'Direct Expense'),
                    ('Rent', 'Indirect Expense'), ('Electricity', 'Indirect Expense'),
                    ('Telephone', 'Indirect Expense'), ('Office Supplies', 'Indirect Expense'),
                    ('Travelling', 'Indirect Expense'), ('Printing & Stationery', 'Indirect Expense'),
                    ('Miscellaneous Expenses', 'Indirect Expense'),
                    ('Furniture & Fixtures', 'Fixed Assets'), ('Computer & Peripherals', 'Fixed Assets'),
                    ('Office Equipment', 'Fixed Assets'), ('Vehicles', 'Fixed Assets'),
                    ('Cash in Hand', 'Current Assets'), ('Bank Accounts (PNB)', 'Current Assets'),
                    ('Stock in Trade', 'Current Assets'), ('Sundry Debtors', 'Current Assets'),
                    ('Prepaid Expenses', 'Current Assets'),
                    ('Sundry Creditors', 'Current Liabilities'),
                    ('GST Payable (CGST)', 'Current Liabilities'),
                    ('GST Payable (SGST)', 'Current Liabilities'),
                    ('GST Payable (IGST)', 'Current Liabilities'),
                    ('TDS Payable', 'Current Liabilities'),
                    ('Outstanding Expenses', 'Current Liabilities'),
                    ("Owner's Capital", 'Capital Account'), ("Owner's Drawings", 'Capital Account'),
                ]
                for name, acc_type in default_accounts:
                    _db.session.add(AccountHead(name=name, account_type=acc_type, is_default=True))
                _db.session.commit()

        print("  [OK]   Database initialised.")
    except Exception as exc:
        print(f"  [WARN] Could not initialise database automatically: {exc}")


# ---------------------------------------------------------------------------
# Browser launcher (delayed so the server is ready first)
# ---------------------------------------------------------------------------

def _open_browser():
    webbrowser.open('http://localhost:5000')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  NIBRITY ENTERPRISE - GST Billing App            ║")
    print("║  Server running at: http://localhost:5000        ║")
    print("║  Press Ctrl+C to stop                            ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    # Ensure writable directories exist next to the exe
    for folder in ('data', 'exports', 'backups'):
        os.makedirs(os.path.join(EXE_DIR, folder), exist_ok=True)

    # First-run DB setup
    _first_run_setup()

    # Open browser after 1.5-second delay so Flask has time to start
    threading.Timer(1.5, _open_browser).start()

    # Start Flask server (blocks until Ctrl+C)
    from app import create_app
    from config import Config

    flask_app = create_app()
    flask_app.run(host=Config.HOST, port=Config.PORT, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
