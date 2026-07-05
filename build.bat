@echo off
chcp 65001 >nul
REM ============================================================
REM Build Script for Windows — بناء التطبيق التنفيذي
REM ============================================================

echo 📦 ERP Accounting System — Build Script (Windows)
echo ========================================
echo.

REM Check Python
echo 🔍 Checking Python version...
python --version
if errorlevel 1 (
    echo ❌ Python not found! Install Python 3.11+ from https://python.org
    pause
    exit /b 1
)
echo.

REM Install requirements
echo 📥 Installing requirements...
pip install -r requirements.txt
echo.

REM Install PyInstaller
echo 📥 Installing PyInstaller...
pip install pyinstaller
echo.

REM Run tests
echo 🧪 Running tests...
python -m pytest tests\unit\ --no-cov -q
if errorlevel 1 (
    echo ⚠️ Some tests failed, but continuing build...
)
echo.

REM Initialize database
echo 🗄️ Initializing database...
python -m erp_accounting.main --seed
echo.

REM Build executable
echo 🔨 Building executable...
pyinstaller erp_accounting.spec --noconfirm
echo.

REM Check output
if exist "dist\ERP_Accounting\ERP_Accounting.exe" (
    echo ✅ Build successful!
    echo.
    echo 📁 Output: dist\ERP_Accounting\
    echo 🚀 Run: dist\ERP_Accounting\ERP_Accounting.exe
    echo.
    echo 📦 To distribute: Zip the dist\ERP_Accounting\ folder
) else (
    echo ❌ Build failed! Check output above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
pause
