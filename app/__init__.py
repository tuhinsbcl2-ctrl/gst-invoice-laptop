"""
Flask Application Factory
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()


def create_app(config_class=Config):
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

    app.register_blueprint(main_bp)
    app.register_blueprint(invoice_bp, url_prefix='/invoice')
    app.register_blueprint(challan_bp, url_prefix='/challan')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(product_bp, url_prefix='/product')
    app.register_blueprint(expense_bp, url_prefix='/expense')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    with app.app_context():
        db.create_all()

    return app
