#!/bin/bash
# ═════════════════════════════════════════════════════
# ERP Accounting System v10.0 — Linux/macOS Launcher
# ═════════════════════════════════════════════════════

cd "$(dirname "$0")"

echo "═══════════════════════════════════════"
echo "  ERP Accounting System v10.0"
echo "  نظام ERP محاسبي متكامل"
echo "═══════════════════════════════════════"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 غير مثبت!"
    echo "ثبّته من: https://www.python.org/downloads/"
    exit 1
fi

# Check requirements
echo "🔍 Checking requirements..."
if ! python3 -c "import PySide6" &> /dev/null; then
    echo "📥 Installing requirements..."
    pip3 install -r requirements.txt
fi

# Initialize database if needed
if [ ! -f "erp_accounting.db" ]; then
    echo "🗄️ Initializing database..."
    python3 -m erp_accounting.main --seed
    echo ""
    echo "✅ Database initialized!"
    echo "🔑 Default login: admin / Admin@123"
    echo ""
fi

# Run
echo "🚀 Starting ERP Accounting System..."
python3 -m erp_accounting.main
