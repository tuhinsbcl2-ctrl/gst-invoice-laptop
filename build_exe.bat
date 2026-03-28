@echo off
REM build_exe.bat — Double-click to build the standalone Windows .exe
REM
REM Requirements:
REM   Python must be installed and in PATH
REM   pip install -r requirements.txt
REM   pip install pyinstaller

title GST Billing App - Build

echo ============================================================
echo   NIBRITY ENTERPRISE - GST Billing App Builder
echo ============================================================
echo.

REM Check Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in PATH.
    echo         Please install Python from https://www.python.org/downloads/
    echo         and make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Install/upgrade PyInstaller
echo [INFO] Installing/upgrading PyInstaller...
pip install --quiet --upgrade pyinstaller
if %errorlevel% neq 0 (
    echo [ERROR] Could not install PyInstaller.
    pause
    exit /b 1
)

REM Run the build script
echo.
echo [INFO] Starting build...
echo.
python build_exe.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed. See messages above.
    pause
    exit /b 1
)

echo.
echo Build complete!  Output is in the dist\GSTBillingApp\ folder.
echo.
pause
