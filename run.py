"""
Entry point to start the GST Billing Application.
Run: python run.py
"""
from app import create_app
from config import Config

app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("  NIBRITY ENTERPRISE - GST Accounting Application")
    print("=" * 60)
    print(f"  Starting server at http://{Config.HOST}:{Config.PORT}")
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
