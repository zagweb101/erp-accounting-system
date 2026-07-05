#!/bin/bash
# ============================================================
# Build Script — بناء التطبيق التنفيذي
# ============================================================
# يحوّل المشروع إلى ملف تنفيذي (.exe على ويندوز، binary على لينكس/ماك)
#
# Usage:
#   chmod +x build.sh
#   ./build.sh
#
# المتطلبات:
#   pip install pyinstaller
# ============================================================

set -e  # Exit on error

echo "📦 ERP Accounting System — Build Script"
echo "========================================"
echo ""

# Check Python version
echo "🔍 Checking Python version..."
python3 --version
echo ""

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt
echo ""

# Install PyInstaller
echo "📥 Installing PyInstaller..."
pip install pyinstaller
echo ""

# Run tests
echo "🧪 Running tests..."
python3 -m pytest tests/unit/ --no-cov -q || {
    echo "⚠️ Some tests failed, but continuing build..."
}
echo ""

# Initialize database
echo "🗄️ Initializing database..."
python3 -m erp_accounting.main --seed
echo ""

# Build executable
echo "🔨 Building executable..."
pyinstaller erp_accounting.spec --noconfirm
echo ""

# Check output
if [ -d "dist/ERP_Accounting" ]; then
    echo "✅ Build successful!"
    echo ""
    echo "📁 Output location: dist/ERP_Accounting/"
    echo ""
    echo "🚀 To run:"
    if [ "$(uname)" == "Darwin" ] || [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        echo "  ./dist/ERP_Accounting/ERP_Accounting"
    else
        echo "  dist\\ERP_Accounting\\ERP_Accounting.exe"
    fi
    echo ""
    echo "📦 To distribute:"
    echo "  Zip the dist/ERP_Accounting/ folder"
else
    echo "❌ Build failed! Check the output above."
    exit 1
fi

echo ""
echo "========================================"
echo "Build complete!"
