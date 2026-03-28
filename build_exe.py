"""
build_exe.py — Build the standalone Windows .exe using PyInstaller.

Usage:
    python build_exe.py

Requirements:
    pip install pyinstaller
    (all other requirements must also be installed)

Output:
    dist/GSTBillingApp/GSTBillingApp.exe
"""

import subprocess
import sys
import os


def check_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[ERROR] PyInstaller is not installed.")
        print("        Run:  pip install pyinstaller")
        sys.exit(1)


def main():
    print("=" * 60)
    print("  NIBRITY ENTERPRISE - GST Billing App Builder")
    print("=" * 60)

    check_pyinstaller()

    spec_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run_app.spec')
    if not os.path.exists(spec_file):
        print(f"[ERROR] Spec file not found: {spec_file}")
        sys.exit(1)

    print()
    print("  Building exe — this may take a few minutes...")
    print()

    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', '--clean', spec_file],
        check=False,
    )

    if result.returncode != 0:
        print()
        print("[ERROR] Build failed. Check the output above for details.")
        sys.exit(result.returncode)

    print()
    print("=" * 60)
    print("  Build successful!")
    print()
    print("  Output:  dist/GSTBillingApp/GSTBillingApp.exe")
    print()
    print("  To run:  double-click dist/GSTBillingApp/GSTBillingApp.exe")
    print("           (or copy the entire dist/GSTBillingApp/ folder to")
    print("            any Windows PC — no Python required!)")
    print("=" * 60)


if __name__ == '__main__':
    main()
