@echo off
title ERP Accounting System v10.0
color 0B

echo ═══════════════════════════════════════
echo   ERP Accounting System v10.0
echo   نظام ERP محاسبي متكامل
echo ═══════════════════════════════════════
echo.

:: Change to script directory
cd /d "%~dp0"

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python غير مثبت!
    echo.
    echo يرجى تثبيت Python 3.11+ من: https://www.python.org/downloads/
    echo مهم: فعّل خيار "Add Python to PATH" عند التثبيت
    echo.
    pause
    exit /b 1
)

:: Check if requirements are installed
echo 🔍 Checking requirements...
pip show PySide6 >nul 2>&1
if errorlevel 1 (
    echo 📥 Installing requirements...
    pip install -r requirements.txt
    echo.
)

:: Check if database exists
if not exist "erp_accounting.db" (
    echo 🗄️ Initializing database...
    python -m erp_accounting.main --seed
    echo.
    echo ✅ Database initialized!
    echo.
    echo 🔑 Default login:
    echo    Username: admin
    echo    Password: Admin@123
    echo.
)

:: Run the application
echo 🚀 Starting ERP Accounting System...
python -m erp_accounting.main

:: If the app crashes, keep window open
if errorlevel 1 (
    echo.
    echo ❌ Application exited with error.
    pause
)
