# Building the Standalone Windows .exe

This guide explains how to package the GST Billing App into a
`GSTBillingApp.exe` that runs on **any Windows PC without installing Python**.

---

## Prerequisites (one-time, on the build machine)

The build machine **must** have Python installed.  The target PCs do **not**.

1. **Install Python 3.10 or higher** — <https://www.python.org/downloads/>  
   ✅ During installation, check **"Add Python to PATH"**.

2. **Install all dependencies** (open Command Prompt in the project folder):

   ```bat
   python -m pip install -r requirements-dev.txt
   ```

3. *(Optional but recommended)* Work inside a virtual environment:

   ```bat
   python -m venv venv
   venv\Scripts\activate
   python -m pip install -r requirements-dev.txt
   ```

---

## Building the .exe

### Option A — Double-click (easiest)

1. Double-click **`build_exe.bat`** in the project folder.
2. Wait a few minutes while PyInstaller packages everything.
3. The output is placed in `dist\GSTBillingApp\`.

### Option B — Command line

```bat
python build_exe.py
```

Or run PyInstaller directly with the spec file:

```bat
pyinstaller --clean run_app.spec
```

---

## No CMD Window (Windowed Mode)

The build is configured with `console=False` in `run_app.spec`.  
This means **double-clicking the `.exe` opens the app directly in the browser — no black CMD window appears**.

The app starts a local Flask server in the background and automatically opens your default browser.

> **If the app doesn't open:** manually browse to <http://localhost:5000>

---

## Output Structure

After a successful build you will find:

```
dist/
└── GSTBillingApp/
    ├── GSTBillingApp.exe      ← Double-click to run (no CMD window)
    ├── data/                  ← Created automatically on first run
    │   └── gst_billing.db     ← Your database (all invoices & settings)
    ├── exports/               ← Generated PDFs, Excel files
    ├── backups/               ← Backup ZIP files
    └── [PyInstaller internals]
```

> **The `data/` folder is created automatically the first time the app runs.**
> Company details and the invoice sequence are seeded on first launch.

---

## Distributing to Another PC

1. Copy the **entire `dist\GSTBillingApp\` folder** to the target PC
   (via USB drive, shared folder, Google Drive, etc.).
2. On the target PC, **double-click `GSTBillingApp.exe`**.
3. The browser opens automatically at **<http://localhost:5000>**.
4. Start billing! 🎉

No Python, no pip, no terminal commands needed on the target PC.

---

## Migrating Your Data

Your business data lives **entirely** in one file:

```
GSTBillingApp\data\gst_billing.db
```

To move data to a new PC (or a new build):

1. Copy `data\gst_billing.db` from the old machine.
2. Paste it into the `data\` folder next to the exe on the new machine.
3. Run `GSTBillingApp.exe` — all your invoices and settings are restored.

> The app automatically runs database migrations on startup, so columns added in new versions are added to your existing database without losing data.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Build fails with "module not found" | Run `python -m pip install -r requirements-dev.txt` again, then rebuild |
| Antivirus blocks the .exe | Add `dist\GSTBillingApp\` as an exception in your antivirus |
| Browser does not open automatically | Open `http://localhost:5000` manually |
| Port 5000 already in use | Close other apps using port 5000, then try again |
| App data is lost after updating exe | Always preserve the `data\gst_billing.db` file across updates |
| Reports show 500 error on old database | The startup migration should fix this automatically; check the log |

---

## Rebuilding After Code Changes

After modifying the app source code:

1. Run `build_exe.bat` (or `python build_exe.py`) again.
2. Replace the old `dist\GSTBillingApp\` folder on target PCs with the new one.
3. **Keep** the `data\gst_billing.db` file — never overwrite it with the new build.
