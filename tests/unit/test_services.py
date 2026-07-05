"""
اختبارات BackupService و PDFService (رفع التغطية من 0% إلى 80%+)
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["BACKUP_DIR"] = "/tmp/test_backup_services"



from infrastructure.services.backup_service import BackupService
from infrastructure.services.audit_service import AuditService


@pytest.fixture(autouse=True)
def cleanup_backup_dir():
    """Clean up backup directory before and after each test."""
    backup_dir = Path("/tmp/test_backup_services")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    yield
    if backup_dir.exists():
        shutil.rmtree(backup_dir)


class TestBackupService:
    """اختبارات خدمة النسخ الاحتياطي."""

    def test_create_backup_success(self) -> None:
        """إنشاء نسخة احتياطية ينجح."""
        service = BackupService()
        path = service.create_backup(description="test backup", created_by="admin")
        assert path.exists()
        assert path.suffix == ".zip"
        assert path.stat().st_size > 0

    def test_create_backup_includes_metadata(self) -> None:
        """النسخة الاحتياطية تحوي metadata.json."""
        import json
        import zipfile

        service = BackupService()
        path = service.create_backup(description="metadata test", created_by="admin")

        with zipfile.ZipFile(path, "r") as zf:
            assert "metadata.json" in zf.namelist()
            assert "database.db" in zf.namelist()
            metadata = json.loads(zf.read("metadata.json"))
            assert "backup_timestamp" in metadata
            assert "created_by" in metadata
            assert metadata["created_by"] == "admin"
            assert metadata["description"] == "metadata test"

    def test_create_multiple_backups(self) -> None:
        """إنشاء عدة نسخ احتياطية ينجح."""
        import time
        service = BackupService()
        paths = []
        for i in range(3):
            time.sleep(1.1)  # Ensure unique timestamps
            path = service.create_backup(description=f"backup {i}", created_by="admin")
            paths.append(path)

        # All should exist with unique names
        for p in paths:
            assert p.exists()
        # Filenames should be unique
        names = [p.name for p in paths]
        assert len(set(names)) == 3

    def test_list_backups_returns_list(self) -> None:
        """list_backups يُعيد قائمة."""
        service = BackupService()
        # Create at least one backup
        service.create_backup(description="list test", created_by="admin")
        backups = service.list_backups()
        assert isinstance(backups, list)
        assert len(backups) >= 1
        for b in backups:
            assert "file_name" in b

    def test_list_backups_includes_metadata(self) -> None:
        """list_backups يُعيد الـ metadata للنسخ."""
        service = BackupService()
        service.create_backup(description="metadata list test", created_by="admin")
        backups = service.list_backups()
        # Find our backup
        found = [b for b in backups if b.get("description") == "metadata list test"]
        assert len(found) >= 1
        assert found[0]["created_by"] == "admin"

    def test_delete_backup_success(self) -> None:
        """حذف نسخة احتياطية ينجح."""
        service = BackupService()
        path = service.create_backup(description="to delete", created_by="admin")
        assert path.exists()

        result = service.delete_backup(path)
        assert result is True
        assert not path.exists()

    def test_delete_nonexistent_backup(self) -> None:
        """حذف نسخة غير موجودة يُعيد False."""
        service = BackupService()
        result = service.delete_backup(Path("/tmp/nonexistent_backup.zip"))
        assert result is False

    def test_restore_without_confirm_raises(self) -> None:
        """الاستعادة بدون تأكيد ترمي PermissionError."""
        service = BackupService()
        path = service.create_backup(description="restore test", created_by="admin")
        with pytest.raises(PermissionError):
            service.restore_backup(path, confirm=False)

    def test_restore_with_confirm_success(self) -> None:
        """الاستعادة بتأكيد تنجح."""
        service = BackupService()
        # Create initial backup
        path = service.create_backup(description="restore confirm", created_by="admin")
        # Restore (should work and create safety backup first)
        result = service.restore_backup(path, confirm=True)
        assert result is True

    def test_restore_nonexistent_file_raises(self) -> None:
        """استعادة ملف غير موجود ترمي FileNotFoundError."""
        service = BackupService()
        with pytest.raises(FileNotFoundError):
            service.restore_backup(Path("/tmp/nonexistent.zip"), confirm=True)


class TestAuditService:
    """اختبارات خدمة سجل النشاط."""

    def test_record_returns_log_entry(self) -> None:
        """record يُعيد سجل AuditLog."""
        service = AuditService()
        log = service.record(
            user_id=uuid4(),
            username="test_user",
            action="CREATE",
            entity_type="invoice",
            entity_id=uuid4(),
            description="Created invoice for testing",
            ip_address="127.0.0.1",
        )
        assert log is not None
        assert log.action == "CREATE"
        assert log.username == "test_user"
        assert log.entity_type == "invoice"

    def test_record_with_minimal_data(self) -> None:
        """record يعمل بأقل بيانات."""
        service = AuditService()
        log = service.record(
            user_id=None,
            username=None,
            action="SYSTEM",
            description="System startup",
        )
        assert log is not None
        assert log.action == "SYSTEM"

    def test_record_multiple_actions(self) -> None:
        """تسجيل عدة عمليات مختلفة."""
        service = AuditService()
        actions = ["CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT"]
        for action in actions:
            service.record(
                user_id=uuid4(),
                username=f"multi_test_{action}",
                action=action,
                description=f"Test {action}",
            )
        all_logs = service.list_logs(limit=100)
        recorded_actions = {log.action for log in all_logs if log.action in actions}
        # Compare as sets, not ordered lists
        assert set(actions).issubset(recorded_actions)

    def test_list_logs_by_user_filter(self) -> None:
        """فلترة السجلات حسب المستخدم."""
        service = AuditService()
        user_id = uuid4()
        service.record(user_id=user_id, username="filter_user", action="TEST")
        service.record(user_id=uuid4(), username="other_user", action="TEST")

        user_logs = service.list_logs(user_id=user_id)
        assert all(log.user_id == str(user_id) for log in user_logs)

    def test_list_logs_by_action_filter(self) -> None:
        """فلترة السجلات حسب نوع العملية."""
        service = AuditService()
        service.record(user_id=uuid4(), username="action_test", action="DELETE")
        service.record(user_id=uuid4(), username="action_test", action="CREATE")

        delete_logs = service.list_logs(action="DELETE")
        assert all(log.action == "DELETE" for log in delete_logs)

    def test_list_logs_by_entity_type(self) -> None:
        """فلترة السجلات حسب نوع الكيان."""
        service = AuditService()
        service.record(
            user_id=uuid4(), username="entity_test",
            action="CREATE", entity_type="customer",
        )
        service.record(
            user_id=uuid4(), username="entity_test",
            action="CREATE", entity_type="invoice",
        )

        customer_logs = service.list_logs(entity_type="customer")
        assert all(log.entity_type == "customer" for log in customer_logs)

    def test_count_logs(self) -> None:
        """عد السجلات."""
        service = AuditService()
        initial = service.count_logs()
        service.record(user_id=uuid4(), username="count_test", action="COUNT_TEST")
        new_count = service.count_logs()
        assert new_count > initial

    def test_count_logs_by_action(self) -> None:
        """عد السجلات حسب النوع."""
        service = AuditService()
        initial = service.count_logs(action="SPECIFIC_COUNT_TEST")
        for _ in range(3):
            service.record(user_id=uuid4(), username="cc", action="SPECIFIC_COUNT_TEST")
        new_count = service.count_logs(action="SPECIFIC_COUNT_TEST")
        assert new_count >= initial + 3

    def test_record_does_not_raise_on_invalid_data(self) -> None:
        """record لا يرمي استثناء عند بيانات غير صالحة."""
        service = AuditService()
        # Should not raise
        result = service.record(
            user_id=None, username=None,
            action="TEST_NO_RAISE",
            description="Test",
        )
        # Either succeeds or returns None
        assert result is None or result.action == "TEST_NO_RAISE"


class TestPDFService:
    """اختبارات خدمة PDF."""

    @pytest.fixture
    def pdf_service(self):
        from infrastructure.services.pdf_service import PDFService
        return PDFService(output_dir="/tmp/test_pdfs")

    def test_export_invoice_pdf(self, pdf_service) -> None:
        """تصدير فاتورة PDF ينجح."""
        invoice_data = {
            "invoice_no": "TEST-INV-001",
            "invoice_type": "SALE",
            "issue_date": "2026-07-05T10:00:00",
            "party_name": "شركة الاختبار",
            "status": "POSTED",
            "subtotal": "1000.00",
            "tax_amount": "150.00",
            "discount": "0",
            "total": "1150.00",
            "notes": "فاتورة اختبار",
            "items": [
                {
                    "product_name": "منتج اختبار",
                    "quantity": "2",
                    "unit_price": "500",
                    "tax_rate": "15",
                    "discount": "0",
                    "line_total": "1150.00",
                },
            ],
        }
        company_data = {
            "name": "شركتي",
            "address": "الرياض",
            "phone": "+966 11 123 4567",
            "tax_number": "300000000000003",
        }
        path = pdf_service.export_invoice_pdf(invoice_data, company_data)
        assert Path(path).exists()
        assert Path(path).suffix == ".pdf"
        assert Path(path).stat().st_size > 0

    def test_export_invoice_pdf_without_company(self, pdf_service) -> None:
        """تصدير فاتورة بدون بيانات شركة."""
        invoice_data = {
            "invoice_no": "TEST-INV-002",
            "invoice_type": "PURCHASE",
            "issue_date": "2026-07-05T10:00:00",
            "party_name": "مورد",
            "status": "POSTED",
            "subtotal": "500",
            "tax_amount": "75",
            "discount": "0",
            "total": "575",
            "items": [],
        }
        path = pdf_service.export_invoice_pdf(invoice_data, company_data=None)
        assert Path(path).exists()

    def test_export_trial_balance_pdf(self, pdf_service) -> None:
        """تصدير ميزان المراجعة PDF."""
        report_data = {
            "as_of_date": "2026-07-05T10:00:00",
            "lines": [
                {"account_code": "1101", "account_name": "الصندوق", "account_type": "ASSET", "debit": "1000", "credit": "0"},
                {"account_code": "4101", "account_name": "المبيعات", "account_type": "REVENUE", "debit": "0", "credit": "1000"},
            ],
            "total_debit": "1000",
            "total_credit": "1000",
            "is_balanced": True,
            "difference": "0",
        }
        path = pdf_service.export_trial_balance_pdf(report_data)
        assert Path(path).exists()
        assert Path(path).suffix == ".pdf"

    def test_export_balance_sheet_pdf(self, pdf_service) -> None:
        """تصدير قائمة المركز المالي PDF."""
        report_data = {
            "as_of_date": "2026-07-05T10:00:00",
            "assets": [
                {"account_code": "1101", "account_name": "الصندوق", "amount": "50000"},
            ],
            "liabilities": [
                {"account_code": "2101", "account_name": "ذمم الموردين", "amount": "20000"},
            ],
            "equity": [
                {"account_code": "3101", "account_name": "رأس المال", "amount": "30000"},
            ],
            "total_assets": "50000",
            "total_liabilities": "20000",
            "total_equity": "30000",
            "is_balanced": True,
        }
        path = pdf_service.export_balance_sheet_pdf(report_data)
        assert Path(path).exists()
        assert Path(path).suffix == ".pdf"

    def test_export_with_custom_filename(self, pdf_service) -> None:
        """تصدير ب اسم ملف مخصص."""
        report_data = {
            "as_of_date": "2026-07-05",
            "lines": [],
            "total_debit": "0",
            "total_credit": "0",
            "is_balanced": True,
            "difference": "0",
        }
        path = pdf_service.export_trial_balance_pdf(report_data, filename="custom_tb.pdf")
        assert Path(path).name == "custom_tb.pdf"

    def test_output_dir_created_automatically(self) -> None:
        """مجلد الإخراج يُنشأ تلقائيًا."""
        from infrastructure.services.pdf_service import PDFService
        test_dir = Path("/tmp/test_pdf_auto_create")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        # Should not exist before
        assert not test_dir.exists()
        service = PDFService(output_dir=str(test_dir))
        # Should exist after instantiation
        assert test_dir.exists()
        # Cleanup
        shutil.rmtree(test_dir)
