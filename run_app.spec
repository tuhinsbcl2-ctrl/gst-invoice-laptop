# -*- mode: python ; coding: utf-8 -*-
#
# run_app.spec — PyInstaller spec file for GSTBillingApp
#
# Build command:  pyinstaller run_app.spec
# Output:         dist/GSTBillingApp/GSTBillingApp.exe
#
# NOTE: Run this on a Windows machine that has Python and all
# requirements installed (pip install -r requirements-dev.txt).

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# ---------------------------------------------------------------------------
# Hidden imports — packages that PyInstaller may miss through static analysis
# ---------------------------------------------------------------------------
hidden_imports = (
    collect_submodules('flask') +
    collect_submodules('flask_sqlalchemy') +
    collect_submodules('sqlalchemy') +
    collect_submodules('jinja2') +
    collect_submodules('markupsafe') +
    collect_submodules('werkzeug') +
    collect_submodules('click') +
    collect_submodules('itsdangerous') +
    collect_submodules('num2words') +
    collect_submodules('openpyxl') +
    collect_submodules('PIL') +
    collect_submodules('lxml') +
    collect_submodules('xhtml2pdf') +
    collect_submodules('reportlab') +
    collect_submodules('html5lib') +
    collect_submodules('arabic_reshaper') +
    collect_submodules('bidi') +
    [
        'sqlite3',
        'email.mime.text',
        'email.mime.multipart',
    ]
)

# ---------------------------------------------------------------------------
# Data files — templates, static assets, and anything else the app needs at
# runtime.  Format: (source_path, dest_folder_inside_bundle)
# ---------------------------------------------------------------------------
datas = [
    # Flask templates
    (os.path.join('app', 'templates'), os.path.join('app', 'templates')),
    # Static files (CSS / JS / images)
    (os.path.join('app', 'static'),    os.path.join('app', 'static')),
]

# Include xhtml2pdf / reportlab data files if present
try:
    datas += collect_data_files('xhtml2pdf')
except Exception:
    pass

try:
    datas += collect_data_files('reportlab')
except Exception:
    pass

try:
    datas += collect_data_files('html5lib')
except Exception:
    pass

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    ['launcher.py'],          # Entry point
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---------------------------------------------------------------------------
# One-folder distribution (--onedir) — faster startup than --onefile because
# files are not extracted on every run.  The user distributes the whole
# GSTBillingApp/ folder.
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GSTBillingApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,       # Disable UPX — avoids antivirus false positives and slow startup
    console=False,   # No CMD window — double-click to run silently
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,       # Set to 'app/static/img/icon.ico' if you have an icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,       # Disable UPX — avoids antivirus false positives and slow startup
    upx_exclude=[],
    name='GSTBillingApp',
)
