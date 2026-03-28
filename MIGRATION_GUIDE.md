# Migration Guide – Moving GST Billing App to Another Laptop

This guide explains how to transfer the NIBRITY ENTERPRISE GST Billing Application to a new computer without losing any data.

---

## Understanding the Data

**All your business data lives in exactly one file:**
```
gst-invoice-laptop/data/gst_billing.db
```

Everything else (the code, templates, static files) is the **application** — it can be re-downloaded at any time. The `.db` file is what you **must** protect and copy.

---

## Method 1: USB Drive / Direct Copy (Easiest)

### On the old laptop:
1. Plug in a USB drive
2. Copy the entire `gst-invoice-laptop/` folder to the USB drive
   ```
   (Right-click → Copy → Paste to USB)
   ```

### On the new laptop:
1. Install Python 3.8+ from https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation
2. Copy the `gst-invoice-laptop/` folder from USB to your desired location (e.g. `C:\Users\YourName\`)
3. Open Command Prompt (Windows) or Terminal (Mac/Linux)
4. Navigate to the folder:
   ```bash
   cd C:\Users\YourName\gst-invoice-laptop
   ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Start the application:
   ```bash
   python run.py
   ```
7. Open **http://127.0.0.1:5000** in your browser — all your data is there!

---

## Method 2: Git Clone (For Developers)

This method separates code from data.

### Push code to GitHub:
```bash
cd gst-invoice-laptop
git add .
git commit -m "update app"
git push origin main
```

> **Note:** `data/gst_billing.db` is in `.gitignore` — it is NOT pushed to GitHub. This is intentional to protect your business data.

### On the new laptop:
1. Install Python 3.8+
2. Clone the repository:
   ```bash
   git clone https://github.com/tuhinsbcl2-ctrl/gst-invoice-laptop.git
   cd gst-invoice-laptop
   ```
3. **Copy your database file** from the old laptop:
   - Copy `data/gst_billing.db` via USB / email / cloud storage
   - Place it in the `data/` folder of the cloned repo
4. Install and run:
   ```bash
   pip install -r requirements.txt
   python run.py
   ```

---

## Method 3: Backup & Restore (Built-in Feature)

The app has a built-in backup/restore feature.

### To create a backup:
1. Open the app: http://127.0.0.1:5000
2. Go to **Reports → Backup DB**
3. A ZIP file (`backup_YYYYMMDD_HHMMSS.zip`) will be downloaded to your browser's downloads folder
4. Store this ZIP on USB / cloud / email

### To restore on a new laptop:
1. Install the app on the new laptop (follow Method 1 steps 1–5)
2. Run `python setup.py` to create an empty database
3. Open the app: http://127.0.0.1:5000
4. Go to **Reports → Restore DB**
5. Upload the backup ZIP file
6. Restart the app: `python run.py`
7. All your data is restored!

---

## Database-Only Migration

If you only want to transfer your business data (not the full code):

1. Copy just this one file: `data/gst_billing.db`
2. On the new laptop (after installing the app fresh):
   - Stop the app
   - Replace `data/gst_billing.db` with your copy
   - Start the app again

---

## Automated Daily Backup (Recommended)

### Windows: Create a scheduled task
1. Create a file `backup_daily.bat`:
   ```bat
   @echo off
   cd C:\path\to\gst-invoice-laptop
   xcopy data\gst_billing.db "D:\GST_Backups\gst_billing_%date:~10,4%%date:~4,2%%date:~7,2%.db" /Y
   ```
2. Open Task Scheduler → Create Basic Task → Daily → Run `backup_daily.bat`

### Linux/Mac: Cron job
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 11 PM):
0 23 * * * cp /path/to/gst-invoice-laptop/data/gst_billing.db /path/to/backups/gst_billing_$(date +\%Y\%m\%d).db
```

---

## Troubleshooting

### "Python not found"
- Reinstall Python from https://www.python.org/downloads/
- Make sure "Add Python to PATH" is checked

### "Module not found" error
```bash
pip install -r requirements.txt
```

### App starts but shows no data
- Your `data/gst_billing.db` is missing or in the wrong place
- Copy it from the old laptop

### Port 5000 already in use
- Change the port in `config.py`: `PORT = 5001`
- Then access: http://127.0.0.1:5001

---

## File Checklist for Migration

| File / Folder | Must Copy? | Notes |
|---|---|---|
| `data/gst_billing.db` | **YES** | All your invoices, customers, products |
| `requirements.txt` | Yes | Needed for fresh install |
| `run.py`, `setup.py`, `config.py` | Yes | App entry points |
| `app/` folder | Yes | All application code |
| `backups/` folder | Optional | Previous backup ZIPs |
| `exports/` folder | Optional | Previously generated PDFs/Excel |

**Minimum required:** Copy the entire `gst-invoice-laptop/` folder.
