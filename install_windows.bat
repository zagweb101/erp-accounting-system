@echo off
chcp 65001 >nul
title ERP Accounting System - Installer
color 0A

echo ═══════════════════════════════════════════════════
echo   📦 ERP Accounting System - Windows Installer
echo ═══════════════════════════════════════════════════
echo.

echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found!
    echo Please install Python from: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYVER=%%i
echo ✅ %PYVER%
echo.

echo [2/5] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo ✅ pip updated
echo.

echo [3/5] Installing requirements...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ⚠️ Some packages failed. Trying individual installs...
    pip install PySide6 --quiet
    pip install SQLAlchemy --quiet
    pip install alembic --quiet
    pip install bcrypt --quiet
    pip install reportlab --quiet
    pip install openpyxl --quiet
    pip install Pillow --quiet
    pip install pydantic --quiet
    pip install pydantic-settings --quiet
    pip install loguru --quiet
    pip install arabic-reshaper --quiet
    pip install python-bidi --quiet
)
echo ✅ Requirements installed
echo.

echo [4/5] Setting up environment...
if not exist ".env" (
    copy .env.example .env >nul
    echo ✅ .env file created
) else (
    echo ✅ .env already exists
)
echo.

echo [5/5] Initializing database...
python main.py --seed
echo.

echo ═══════════════════════════════════════════════════
echo   ✅ Installation Complete!
echo ═══════════════════════════════════════════════════
echo.
echo 🔐 Login credentials:
echo    Username: admin
echo    Password: Admin@123
echo.
echo 🚀 To start the application:
echo    Double-click: start.bat
echo    OR run: python main.py
echo.
echo ⚠️  Change password after first login!
echo.
pause
