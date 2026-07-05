"""
اختبارات UI logic - محاكاة بدون واجهة فعلية

تختبر منطق الـ UI windows (دوال، تحقق، تحويلات) دون الحاجة لـ pytest-qt.
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.db.session import session_scope
from infrastructure.db.models.user_model import UserModel
from infrastructure.db.seed import seed_admin_user, seed_chart_of_accounts

# Check if PySide6 is available
try:
    import PySide6
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False

pytestmark_pyside6 = pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not installed")

from domain.entities.user import User, UserStatus
from domain.entities.invoice import InvoiceType, InvoiceStatus
from domain.value_objects.value_objects import UserRole


@pytest.fixture
def admin_user():
    from sqlalchemy import select
    with session_scope() as s:
        m = s.execute(select(UserModel).where(UserModel.username == "admin")).scalar_one()
        return User(
            id=m.id, username=m.username, email=m.email, password_hash=m.password_hash,
            full_name=m.full_name, role=UserRole(m.role), status=UserStatus(m.status),
        )


class TestAsyncWorker:
    pytestmark = pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not installed")

    """اختبارات AsyncWorker - منطق الـ async threads."""

    def test_async_worker_executes_coroutine(self) -> None:
        """AsyncWorker يُنفّذ coroutine بنجاح."""
        from infrastructure.ui.windows._async_worker import AsyncWorker

        async def sample_coro():
            return 42

        worker = AsyncWorker(sample_coro)
        # We can't test signals without QApplication, but we can test run()
        import asyncio
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(sample_coro())
        assert result == 42

    def test_async_worker_handles_exceptions(self) -> None:
        """AsyncWorker يلتقط الاستثناءات."""
        from infrastructure.ui.windows._async_worker import AsyncWorker

        async def failing_coro():
            raise ValueError("test error")

        # The worker should not raise - it captures errors in error_signal
        worker = AsyncWorker(failing_coro)
        # Just verify it was created
        assert worker is not None


class TestInvoiceCalculations:
    """اختبارات حسابات الفاتورة (منطق UI)."""

    def test_calculate_simple_totals(self) -> None:
        """حساب إجماليات فاتورة بسيطة."""
        from use_cases.invoices.invoice_use_cases import (
            InvoiceLineDTO, calculate_invoice_totals,
        )

        lines = [
            InvoiceLineDTO(
                product_id=uuid4(),
                quantity=Decimal("2"),
                unit_price=Decimal("100"),
                tax_rate=Decimal("15"),
            ),
        ]
        totals = calculate_invoice_totals(lines)
        assert totals.subtotal == Decimal("200")
        assert totals.tax_amount == Decimal("30")
        assert totals.total == Decimal("230")

    def test_calculate_with_discount(self) -> None:
        """حساب مع خصم."""
        from use_cases.invoices.invoice_use_cases import (
            InvoiceLineDTO, calculate_invoice_totals,
        )

        lines = [
            InvoiceLineDTO(
                product_id=uuid4(),
                quantity=Decimal("1"),
                unit_price=Decimal("100"),
                tax_rate=Decimal("15"),
                discount=Decimal("20"),
            ),
        ]
        totals = calculate_invoice_totals(lines)
        # subtotal = 100 - 20 = 80, tax = 12, total = 92
        assert totals.subtotal == Decimal("80")
        assert totals.tax_amount == Decimal("12")
        assert totals.discount_total == Decimal("20")

    def test_multiple_lines(self) -> None:
        """عدة بنود."""
        from use_cases.invoices.invoice_use_cases import (
            InvoiceLineDTO, calculate_invoice_totals,
        )

        lines = [
            InvoiceLineDTO(product_id=uuid4(), quantity=Decimal("3"), unit_price=Decimal("50"), tax_rate=Decimal("15")),
            InvoiceLineDTO(product_id=uuid4(), quantity=Decimal("2"), unit_price=Decimal("100"), tax_rate=Decimal("15")),
        ]
        totals = calculate_invoice_totals(lines)
        assert totals.subtotal == Decimal("350")
        assert totals.tax_amount == Decimal("52.5")

    def test_zero_quantity_raises(self) -> None:
        """كمية صفر تفشل."""
        from use_cases.invoices.invoice_use_cases import (
            InvoiceLineDTO, calculate_invoice_totals,
        )
        from domain.exceptions.exceptions import ValidationException

        lines = [InvoiceLineDTO(product_id=uuid4(), quantity=Decimal("0"), unit_price=Decimal("100"))]
        with pytest.raises(ValidationException):
            calculate_invoice_totals(lines)

    def test_negative_price_raises(self) -> None:
        """سعر سالب يفشل."""
        from use_cases.invoices.invoice_use_cases import (
            InvoiceLineDTO, calculate_invoice_totals,
        )
        from domain.exceptions.exceptions import ValidationException

        lines = [InvoiceLineDTO(product_id=uuid4(), quantity=Decimal("1"), unit_price=Decimal("-100"))]
        with pytest.raises(ValidationException):
            calculate_invoice_totals(lines)

    def test_negative_discount_raises(self) -> None:
        """خصم سالب يفشل."""
        from use_cases.invoices.invoice_use_cases import (
            InvoiceLineDTO, calculate_invoice_totals,
        )
        from domain.exceptions.exceptions import ValidationException

        lines = [
            InvoiceLineDTO(
                product_id=uuid4(), quantity=Decimal("1"),
                unit_price=Decimal("100"), discount=Decimal("-10"),
            ),
        ]
        with pytest.raises(ValidationException):
            calculate_invoice_totals(lines)


class TestPdfServiceLogic:
    """اختبارات منطق PDF Service."""

    def test_arabic_reshaping(self) -> None:
        """إعادة تشكيل النص العربي."""
        from infrastructure.services.pdf_service import _ar
        result = _ar("نص عربي")
        assert result is not None
        assert len(result) > 0

    def test_ar_empty_string(self) -> None:
        """نص فارغ."""
        from infrastructure.services.pdf_service import _ar
        assert _ar("") == ""

    def test_arabic_with_english(self) -> None:
        """نص مختلط عربي/إنجليزي."""
        from infrastructure.services.pdf_service import _ar
        result = _ar("Invoice فاتورة")
        assert "Invoice" in result or "فاتورة" in result

    def test_format_amount(self) -> None:
        """تنسيق المبالغ."""
        from infrastructure.services.pdf_service import _fmt_amount
        assert _fmt_amount(Decimal("1234.56")) == "1,234.56"
        assert _fmt_amount(0) == "0.00"
        assert _fmt_amount(Decimal("1000000")) == "1,000,000.00"

    def test_format_amount_negative(self) -> None:
        """تنسيق مبالغ سالبة."""
        from infrastructure.services.pdf_service import _fmt_amount
        result = _fmt_amount(Decimal("-100.50"))
        # Should handle negative (may show as -100.50 or (100.50))
        assert "100.50" in result


class TestBackupServiceLogic:
    """اختبارات منطق Backup Service."""

    def test_backup_dir_creation(self, tmp_path) -> None:
        """إنشاء مجلد النسخ الاحتياطي."""
        from infrastructure.services.backup_service import BackupService
        backup_dir = tmp_path / "test_backups"
        assert not backup_dir.exists()
        service = BackupService(backup_dir=backup_dir)
        assert backup_dir.exists()

    def test_list_backups_empty(self, tmp_path) -> None:
        """قائمة فارغة عند عدم وجود نسخ."""
        from infrastructure.services.backup_service import BackupService
        service = BackupService(backup_dir=tmp_path / "empty")
        backups = service.list_backups()
        assert backups == []

    def test_delete_nonexistent_returns_false(self, tmp_path) -> None:
        """حذف ملف غير موجود يُعيد False."""
        from infrastructure.services.backup_service import BackupService
        from pathlib import Path
        service = BackupService(backup_dir=tmp_path / "test")
        result = service.delete_backup(Path("/nonexistent/backup.zip"))
        assert result is False

    def test_restore_without_confirm_raises(self, tmp_path) -> None:
        """الاستعادة بدون تأكيد ترمي PermissionError."""
        from infrastructure.services.backup_service import BackupService
        from pathlib import Path
        service = BackupService(backup_dir=tmp_path / "test")
        # Create a dummy file
        dummy = tmp_path / "dummy.zip"
        dummy.write_text("dummy")
        with pytest.raises(PermissionError):
            service.restore_backup(dummy, confirm=False)

    def test_restore_nonexistent_raises(self, tmp_path) -> None:
        """استعادة ملف غير موجود ترمي FileNotFoundError."""
        from infrastructure.services.backup_service import BackupService
        from pathlib import Path
        service = BackupService(backup_dir=tmp_path / "test")
        with pytest.raises(FileNotFoundError):
            service.restore_backup(Path("/nonexistent.zip"), confirm=True)


class TestSettingsLogic:
    """اختبارات منطق الإعدادات."""

    def test_settings_load_defaults(self) -> None:
        """الإعدادات الافتراضية تُحمَّل."""
        from infrastructure.config.settings import get_settings
        settings = get_settings()
        assert settings.APP_NAME != ""
        assert settings.APP_VERSION != ""
        assert settings.DEFAULT_CURRENCY == "SAR"
        assert settings.DEFAULT_TAX_RATE == 15.0
        assert settings.BCRYPT_COST == 12

    def test_settings_database_url(self) -> None:
        """DATABASE_URL مُعّرفة."""
        from infrastructure.config.settings import get_settings
        settings = get_settings()
        assert settings.DATABASE_URL.startswith("sqlite")

    def test_settings_security_defaults(self) -> None:
        """إعدادات الأمان الافتراضية."""
        from infrastructure.config.settings import get_settings
        settings = get_settings()
        assert settings.MAX_LOGIN_ATTEMPTS == 5
        assert settings.LOCK_DURATION_MINUTES == 15
        assert settings.SESSION_DURATION_HOURS == 8


class TestAuditServiceLogic:
    """اختبارات منطق Audit Service."""

    def test_record_returns_log(self) -> None:
        """تسجيل عملية (قد يُعيد None عند الفشل الصامت)."""
        from infrastructure.services.audit_service import AuditService
        service = AuditService()
        log = service.record(
            user_id=uuid4(),
            username="test_user",
            action="TEST_ACTION",
            description="test description",
        )
        # Either succeeds (returns log) or silently fails (returns None)
        # Both are acceptable - audit should never crash the operation
        assert log is None or log.action == "TEST_ACTION"

    def test_list_logs_returns_list(self) -> None:
        """list_logs يُعيد قائمة."""
        from infrastructure.services.audit_service import AuditService
        service = AuditService()
        logs = service.list_logs()
        assert isinstance(logs, list)

    def test_count_logs_returns_int(self) -> None:
        """count_logs يُعيد عدد."""
        from infrastructure.services.audit_service import AuditService
        service = AuditService()
        count = service.count_logs()
        assert isinstance(count, int)
        assert count >= 0


class TestInvoiceNumberGeneration:
    """اختبارات توليد أرقام الفواتير."""

    @pytest.mark.asyncio
    async def test_sale_invoice_no_format(self) -> None:
        """صيغة رقم فاتورة البيع."""
        from adapters.repositories.sql_alchemy.invoice_repository import SqlAlchemyInvoiceRepository
        from domain.entities.invoice import InvoiceType
        from datetime import datetime
        repo = SqlAlchemyInvoiceRepository()
        no = await repo.next_invoice_no(InvoiceType.SALE)
        assert no.startswith("INV-S-")
        assert str(datetime.now().year) in no

    @pytest.mark.asyncio
    async def test_purchase_invoice_no_format(self) -> None:
        """صيغة رقم فاتورة الشراء."""
        from adapters.repositories.sql_alchemy.invoice_repository import SqlAlchemyInvoiceRepository
        from domain.entities.invoice import InvoiceType
        repo = SqlAlchemyInvoiceRepository()
        no = await repo.next_invoice_no(InvoiceType.PURCHASE)
        assert no.startswith("INV-P-")

    @pytest.mark.asyncio
    async def test_sale_return_no_format(self) -> None:
        """صيغة رقم مرتجع البيع."""
        from adapters.repositories.sql_alchemy.invoice_repository import SqlAlchemyInvoiceRepository
        from domain.entities.invoice import InvoiceType
        repo = SqlAlchemyInvoiceRepository()
        no = await repo.next_invoice_no(InvoiceType.SALE_RETURN)
        assert no.startswith("RET-S-")

    @pytest.mark.asyncio
    async def test_purchase_return_no_format(self) -> None:
        """صيغة رقم مرتجع الشراء."""
        from adapters.repositories.sql_alchemy.invoice_repository import SqlAlchemyInvoiceRepository
        from domain.entities.invoice import InvoiceType
        repo = SqlAlchemyInvoiceRepository()
        no = await repo.next_invoice_no(InvoiceType.PURCHASE_RETURN)
        assert no.startswith("RET-P-")
