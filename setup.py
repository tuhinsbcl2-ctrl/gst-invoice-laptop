"""
One-click setup script for NIBRITY ENTERPRISE GST Billing Application.
Run: python setup.py
This initialises the database with default company settings.
"""
import os
import sys

def setup():
    print("=" * 60)
    print("  NIBRITY ENTERPRISE - GST Billing App Setup")
    print("=" * 60)

    # Ensure data directory exists
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports'), exist_ok=True)

    try:
        from app import create_app, db
        from app.models import CompanySettings, InvoiceSequence

        app = create_app()
        with app.app_context():
            db.create_all()
            print("  [OK] Database tables created.")

            # Seed default company settings if not present
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
                db.session.add(settings)
                db.session.commit()
                print("  [OK] Default company settings seeded (NIBRITY ENTERPRISE).")
            else:
                print("  [OK] Company settings already present.")

            # Ensure invoice sequence exists for current financial year
            from app.services.invoice_numbering import get_financial_year
            fy = get_financial_year()
            seq = InvoiceSequence.query.filter_by(prefix='NE', financial_year=fy).first()
            if not seq:
                seq = InvoiceSequence(prefix='NE', financial_year=fy, last_serial=0)
                db.session.add(seq)
                db.session.commit()
                print(f"  [OK] Invoice sequence initialised for FY {fy}.")
            else:
                print(f"  [OK] Invoice sequence already present for FY {fy}.")

        print()
        print("  Setup complete! Run: python run.py")
        print("  Then open http://127.0.0.1:5000 in your browser.")
        print("=" * 60)

    except ImportError as e:
        print(f"  [ERROR] Missing dependency: {e}")
        print("  Please run: pip install -r requirements.txt")
        sys.exit(1)

if __name__ == '__main__':
    setup()
