"""
Flask Application Factory
"""
import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config, BUNDLE_DIR

db = SQLAlchemy()


def create_app(config_class=Config):
    # When running as a frozen PyInstaller exe, Flask cannot locate templates/static
    # via __file__ (which points inside the bundle).  Pass explicit paths instead.
    if getattr(sys, 'frozen', False):
        template_folder = os.path.join(BUNDLE_DIR, 'app', 'templates')
        static_folder = os.path.join(BUNDLE_DIR, 'app', 'static')
        app = Flask(__name__,
                    template_folder=template_folder,
                    static_folder=static_folder)
    else:
        app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # Register blueprints
    from app.routes.invoice import invoice_bp
    from app.routes.challan import challan_bp
    from app.routes.customer import customer_bp
    from app.routes.product import product_bp
    from app.routes.expense import expense_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp
    from app.routes.main import main_bp
    from app.routes.accounts import accounts_bp
    from app.routes.supplier import supplier_bp
    from app.routes.purchase import purchase_bp
    from app.routes.bank import bank_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(invoice_bp, url_prefix='/invoice')
    app.register_blueprint(challan_bp, url_prefix='/challan')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(product_bp, url_prefix='/product')
    app.register_blueprint(expense_bp, url_prefix='/expense')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(accounts_bp, url_prefix='/accounts')
    app.register_blueprint(supplier_bp, url_prefix='/supplier')
    app.register_blueprint(purchase_bp, url_prefix='/purchase')
    app.register_blueprint(bank_bp, url_prefix='/bank')

    with app.app_context():
        db.create_all()

    return app
