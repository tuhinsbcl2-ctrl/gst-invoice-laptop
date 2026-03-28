"""
Configuration for GST Billing Application - NIBRITY ENTERPRISE
"""
import os
import sys

# When running as a PyInstaller frozen exe, sys.frozen is True.
# - sys._MEIPASS  → temporary folder where bundled files are extracted (read-only)
# - os.path.dirname(sys.executable) → folder next to the .exe (user-writable, data lives here)
if getattr(sys, 'frozen', False):
    # Running as compiled .exe
    BASE_DIR = os.path.dirname(sys.executable)
    # Internal bundle directory (templates, static, app code)
    BUNDLE_DIR = getattr(sys, '_MEIPASS', BASE_DIR)
else:
    # Running as normal Python script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

DATA_DIR = os.path.join(BASE_DIR, 'data')
EXPORTS_DIR = os.path.join(BASE_DIR, 'exports')
BACKUPS_DIR = os.path.join(BASE_DIR, 'backups')

# Ensure user-writable directories exist (next to .exe or project root)
for d in [DATA_DIR, EXPORTS_DIR, BACKUPS_DIR]:
    os.makedirs(d, exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'nibrity-gst-billing-secret-2024')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(DATA_DIR, 'gst_billing.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_PATH = os.path.join(DATA_DIR, 'gst_billing.db')
    EXPORTS_DIR = EXPORTS_DIR
    BACKUPS_DIR = BACKUPS_DIR
    BASE_DIR = BASE_DIR
    BUNDLE_DIR = BUNDLE_DIR
    HOST = '127.0.0.1'
    PORT = 5000
    DEBUG = False
