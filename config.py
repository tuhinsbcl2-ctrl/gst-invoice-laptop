"""
Configuration for GST Billing Application - NIBRITY ENTERPRISE
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
EXPORTS_DIR = os.path.join(BASE_DIR, 'exports')
BACKUPS_DIR = os.path.join(BASE_DIR, 'backups')

# Ensure directories exist
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
    HOST = '127.0.0.1'
    PORT = 5000
    DEBUG = False
