"""
اختبارات Screen Styler + UI Service Integration
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Check PySide6
try:
    import PySide6
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False


class TestScreenStyler:
    """اختبارات الـ screen styler."""

    pytestmark = pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not installed")

    def test_style_customers_window_exists(self) -> None:
        from infrastructure.ui.theme.screen_styler import style_customers_window
        assert callable(style_customers_window)

    def test_style_products_window_exists(self) -> None:
        from infrastructure.ui.theme.screen_styler import style_products_window
        assert callable(style_products_window)

    def test_style_invoices_window_exists(self) -> None:
        from infrastructure.ui.theme.screen_styler import style_invoices_window
        assert callable(style_invoices_window)

    def test_style_reports_window_exists(self) -> None:
        from infrastructure.ui.theme.screen_styler import style_reports_window
        assert callable(style_reports_window)

    def test_style_suppliers_window_exists(self) -> None:
        from infrastructure.ui.theme.screen_styler import style_suppliers_window
        assert callable(style_suppliers_window)

    def test_style_journal_window_exists(self) -> None:
        from infrastructure.ui.theme.screen_styler import style_journal_window
        assert callable(style_journal_window)

    def test_style_expenses_window_exists(self) -> None:
        from infrastructure.ui.theme.screen_styler import style_expenses_window
        assert callable(style_expenses_window)

    def test_style_backup_window_exists(self) -> None:
        from infrastructure.ui.theme.screen_styler import style_backup_window
        assert callable(style_backup_window)

    def test_style_settings_window_exists(self) -> None:
        from infrastructure.ui.theme.screen_styler import style_settings_window
        assert callable(style_settings_window)

    def test_style_ai_chat_window_exists(self) -> None:
        from infrastructure.ui.theme.screen_styler import style_ai_chat_window
        assert callable(style_ai_chat_window)

    def test_all_style_functions_exist(self) -> None:
        from infrastructure.ui.theme import screen_styler
        functions = [
            "style_customers_window", "style_products_window",
            "style_invoices_window", "style_reports_window",
            "style_suppliers_window", "style_journal_window",
            "style_expenses_window", "style_backup_window",
            "style_settings_window", "style_ai_chat_window",
        ]
        for func_name in functions:
            assert hasattr(screen_styler, func_name), f"Missing: {func_name}"


class TestUIServiceIntegration:
    """اختبارات تكامل الخدمات مع UI."""

    pytestmark = pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not installed")

    def test_export_to_excel_exists(self) -> None:
        from infrastructure.ui.services.ui_service_integration import export_to_excel
        assert callable(export_to_excel)

    def test_import_from_excel_exists(self) -> None:
        from infrastructure.ui.services.ui_service_integration import import_from_excel
        assert callable(import_from_excel)

    def test_send_invoice_email_exists(self) -> None:
        from infrastructure.ui.services.ui_service_integration import send_invoice_email
        assert callable(send_invoice_email)

    def test_scan_invoice_image_exists(self) -> None:
        from infrastructure.ui.services.ui_service_integration import scan_invoice_image
        assert callable(scan_invoice_image)

    def test_check_invoice_anomaly_exists(self) -> None:
        from infrastructure.ui.services.ui_service_integration import check_invoice_anomaly
        assert callable(check_invoice_anomaly)

    def test_get_cash_flow_prediction_exists(self) -> None:
        from infrastructure.ui.services.ui_service_integration import get_cash_flow_prediction
        assert callable(get_cash_flow_prediction)


class TestRequirementsFile:
    """اختبارات ملف المتطلبات."""

    def test_requirements_file_exists(self) -> None:
        req_path = Path(__file__).parent.parent.parent / "requirements.txt"
        assert req_path.exists()

    def test_requirements_contains_core_deps(self) -> None:
        req_path = Path(__file__).parent.parent.parent / "requirements.txt"
        content = req_path.read_text()
        assert "PySide6" in content
        assert "SQLAlchemy" in content
        assert "bcrypt" in content
        assert "reportlab" in content
        assert "openpyxl" in content
        assert "pytest" in content
        assert "alembic" in content

    def test_requirements_contains_optional_deps(self) -> None:
        req_path = Path(__file__).parent.parent.parent / "requirements.txt"
        content = req_path.read_text()
        # These are commented out (optional)
        assert "# openai" in content or "openai" in content
        assert "# pytesseract" in content or "pytesseract" in content

    def test_requirements_contains_arabic_support(self) -> None:
        req_path = Path(__file__).parent.parent.parent / "requirements.txt"
        content = req_path.read_text()
        assert "arabic-reshaper" in content
        assert "python-bidi" in content
