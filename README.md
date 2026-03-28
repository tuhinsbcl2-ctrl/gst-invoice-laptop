# NIBRITY ENTERPRISE – GST Billing Application

A complete, self-contained GST Billing Application for **NIBRITY ENTERPRISE** that runs locally on a laptop with SQLite for full portability.

## Features

- ✅ Automated GST calculation (CGST+SGST for intra-state, IGST for inter-state)
- ✅ Multi-rate HSN support (0%, 5%, 12%, 18%, 28%)
- ✅ Auto-sequencing invoice numbering (NE/001/25-26 format)
- ✅ Tax Invoice PDF (3 copies) + Delivery Challan PDF (4 copies) + Combined 7-page PDF (via xhtml2pdf — pure Python, no native deps)
- ✅ HSN-wise tax breakup table
- ✅ Amount in words (Indian numbering system)
- ✅ Customer/Party management with ledger
- ✅ Product catalog with stock management
- ✅ Expense & payment tracking
- ✅ Excel, CSV, and Tally XML export
- ✅ One-click Backup & Restore

## Quick Start

### Requirements
- Python 3.10+
- pip

### Installation

```bash
# 1. Clone or copy the folder
git clone https://github.com/tuhinsbcl2-ctrl/gst-invoice-laptop.git
cd gst-invoice-laptop

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run one-time setup (creates database + seeds NIBRITY ENTERPRISE defaults)
python setup.py

# 4. Start the application
python run.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Project Structure

```
gst-invoice-laptop/
├── README.md
├── MIGRATION_GUIDE.md       # How to move to another laptop
├── requirements.txt
├── setup.py                 # One-click setup
├── run.py                   # Start the app
├── config.py                # Configuration
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # SQLAlchemy models
│   ├── routes/              # Route handlers
│   ├── services/            # Business logic
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS, JS, images
├── data/
│   └── gst_billing.db       # SQLite database (ALL your business data)
├── backups/                 # Auto-backup ZIP files
└── exports/                 # Generated PDFs, Excel files
```

## Business Data

All business data lives in **`data/gst_billing.db`** — a single SQLite file.
To back it up, just copy that file. To migrate to a new laptop, copy the entire folder.

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed transfer instructions.

## Default Company Settings

The app comes pre-configured for NIBRITY ENTERPRISE:
- **GSTIN**: 19CDOPM2160E1ZH
- **State**: West Bengal (Code: 19)
- **Bank**: Punjab National Bank, SONARGAON branch
- **Invoice Prefix**: NE (format: NE/001/25-26)

Change these in **Settings** after first run.
