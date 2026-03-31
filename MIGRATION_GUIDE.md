# Migration Guide – Moving GST Billing App to Another Laptop

This guide explains how to transfer the GST Billing Application to a new computer without losing any data.

---

## Understanding the Data

**All your business data lives in exactly one file:**
```
gst-invoice-laptop/data/gst_billing.db
```

Everything else (the code, templates, static files) is the **application** — it can be re-downloaded at any time. The `.db` file is what you **must** protect and copy.

> **Good news:** When the app starts on a new machine with an old database, it automatically runs a migration to add any new columns or tables — you will **not** lose existing data.

---

## Method 1: EXE (No Python Required — Recommended for Office Use)

### On the old laptop:
1. Go to **Reports → Backup** to download a backup ZIP.
2. Copy `data/gst_billing.db` to a USB drive or cloud storage.

### On the new laptop:
1. Copy the **entire `dist\GSTBillingApp\` folder** (the built EXE) to the new laptop.
2. **Replace** `data\gst_billing.db` with your backup copy.
3. Double-click **`GSTBillingApp.exe`** — the browser opens automatically.

> See `BUILD_INSTRUCTIONS.md` for how to build the EXE if you don't have it yet.

---

## Method 2: USB Drive / Direct Copy (Python Required)

### On the old laptop:
1. Plug in a USB drive.
2. Copy the entire `gst-invoice-laptop/` folder to the USB drive.

### On the new laptop:
1. Install Python 3.10+ from <https://www.python.org/downloads/>
   - ✅ Check "Add Python to PATH" during installation.
2. Copy the `gst-invoice-laptop/` folder from USB to your desired location (e.g. `C:\Users\YourName\`).
3. Open Command Prompt and navigate to the folder:
   ```bat
   cd C:\Users\YourName\gst-invoice-laptop
   ```
4. Install dependencies:
   ```bat
   pip install -r requirements.txt
   ```
5. Start the application:
   ```bat
   python run.py
   ```
6. Open **http://127.0.0.1:5000** — all your data is there!

---

## Method 3: Backup & Restore (Built-in Feature)

### To create a backup:
1. Open the app: <http://127.0.0.1:5000>
2. Go to **Reports → Backup DB**.
3. A ZIP file (`backup_YYYYMMDD_HHMMSS.zip`) downloads automatically.
4. Save this ZIP to USB / Google Drive / email.

### To restore on a new laptop:
1. Install the app on the new laptop (follow Method 1 or 2 above).
2. Open the app: <http://127.0.0.1:5000>
3. Go to **Reports → Restore DB**.
4. Upload the backup ZIP file.
5. Restart the app.

---

## Google Drive Auto-Backup

You can configure the app to automatically copy each backup to a Google Drive sync folder:

1. Install **Google Drive for Desktop** on your PC — this creates a synced local folder.
2. In the app, go to **Settings** → **Google Drive Backup Folder**.
3. Enter the full local path, e.g.:
   ```
   C:\Users\YourName\Google Drive\GST Backups
   ```
4. From now on, every time you click **Backup**, the ZIP is also copied there and synced to the cloud.

---

## Database-Only Migration

If you only want to transfer your business data (not the full code):

1. Copy just: `data/gst_billing.db`
2. On the new laptop (after installing the app fresh):
   - Stop the app.
   - Replace `data/gst_billing.db` with your copy.
   - Start the app — it will automatically upgrade the schema if needed.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Python not found" | Reinstall Python; check "Add Python to PATH" |
| "Module not found" error | `pip install -r requirements.txt` |
| App starts but shows no data | Your `data/gst_billing.db` is missing or in the wrong place |
| Reports show 500 error | Startup migration should fix this automatically; delete `data/gst_billing.db` and restore from backup if it persists |
| Port 5000 already in use | Close other apps using port 5000, or change port in `config.py` |
| EXE blocked by antivirus | Add the `GSTBillingApp\` folder as an exception in your antivirus |

---

## File Checklist for Migration

| File / Folder | Must Copy? | Notes |
|---|---|---|
| `data/gst_billing.db` | **YES** | All your invoices, customers, products |
| `requirements.txt` | Yes | Needed for fresh Python install |
| `run.py`, `config.py` | Yes | App entry points |
| `app/` folder | Yes | All application code |
| `backups/` folder | Optional | Previous backup ZIPs |
| `exports/` folder | Optional | Previously generated PDFs/Excel |

**Minimum required:** Copy the entire `gst-invoice-laptop/` folder OR copy the entire `dist\GSTBillingApp\` EXE folder.
