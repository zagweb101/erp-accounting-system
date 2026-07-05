"""
اختبارات System Audit - اختبارات الأمان والـ Audit Log
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.db.session import session_scope


from infrastructure.db.models.user_model import UserModel
from infrastructure.db.models.audit_log_model import AuditLogModel

from adapters.repositories.sql_alchemy.invoice_repository import SqlAlchemyInvoiceRepository
from domain.entities.user import User, UserStatus
from domain.entities.invoice import InvoiceType
from domain.value_objects.value_objects import UserRole
from infrastructure.services.audit_service import AuditService


@pytest.fixture
def admin_user():
    from sqlalchemy import select
    with session_scope() as s:
        m = s.execute(select(UserModel).where(UserModel.username == "admin")).scalar_one()
        return User(
            id=m.id, username=m.username, email=m.email, password_hash=m.password_hash,
            full_name=m.full_name, role=UserRole(m.role), status=UserStatus(m.status),
        )


class TestAuditService:
    """اختبارات خدمة سجل النشاط."""

    def test_record_audit_log(self) -> None:
        """تسجيل عملية في سجل النشاط يعمل."""
        service = AuditService()
        log = service.record(
            user_id=uuid4(),
            username="admin",
            action="LOGIN",
            entity_type="user",
            entity_id=uuid4(),
            description="User logged in successfully",
            ip_address="127.0.0.1",
        )
        assert log is not None
        assert log.action == "LOGIN"
        assert log.username == "admin"

    def test_record_multiple_logs(self) -> None:
        """تسجيل عدة عمليات يعمل."""
        service = AuditService()
        for i in range(5):
            service.record(
                user_id=uuid4(),
                username=f"user_{i}",
                action="CREATE",
                entity_type="invoice",
                description=f"Created invoice {i}",
            )
        # Verify all 5 are stored
        all_logs = service.list_logs(limit=100)
        assert len(all_logs) >= 5

    def test_list_logs_by_action(self) -> None:
        """فلترة السجلات حسب نوع العملية."""
        service = AuditService()
        service.record(user_id=uuid4(), username="test", action="DELETE", description="test delete")
        service.record(user_id=uuid4(), username="test", action="CREATE", description="test create")

        deletes = service.list_logs(action="DELETE")
        assert all(log.action == "DELETE" for log in deletes)

    def test_list_logs_by_user(self) -> None:
        """فلترة السجلات حسب المستخدم."""
        service = AuditService()
        user_id = uuid4()
        service.record(user_id=user_id, username="specific_user", action="CREATE")
        service.record(user_id=uuid4(), username="other_user", action="CREATE")

        user_logs = service.list_logs(user_id=user_id)
        assert all(log.user_id == str(user_id) for log in user_logs)

    def test_count_logs(self) -> None:
        """عد السجلات."""
        service = AuditService()
        initial_count = service.count_logs()
        service.record(user_id=uuid4(), username="count_test", action="TEST")
        new_count = service.count_logs()
        assert new_count >= initial_count + 1

    def test_audit_does_not_fail_operation_on_error(self) -> None:
        """سجل النشاط لا يجب أن يوقف العملية التجارية عند فشله."""
        service = AuditService()
        # Pass invalid user_id type - should not raise
        result = service.record(
            user_id=None,
            username=None,
            action="TEST_NO_FAIL",
            description="This should not raise even with None values",
        )
        # Either succeeds or returns None - but doesn't raise
        assert result is None or result.action == "TEST_NO_FAIL"


class TestSecurity:
    """اختبارات أمنية."""

    def test_password_never_stored_in_plain_text(self, admin_user) -> None:
        """كلمة المرور لا تُخزَّن كنص صريح."""
        from sqlalchemy import select
        with session_scope() as s:
            m = s.execute(select(UserModel).where(UserModel.username == "admin")).scalar_one()
            assert m.password_hash != "Admin@123"
            assert m.password_hash.startswith("$2")  # bcrypt prefix
            assert len(m.password_hash) >= 50

    def test_safe_dict_excludes_password(self, admin_user) -> None:
        """to_safe_dict لا يُخرج كلمة المرور."""
        d = admin_user.to_safe_dict()
        assert "password_hash" not in d
        assert "password" not in d

    def test_repr_excludes_password(self, admin_user) -> None:
        """__repr__ لا يُظهر كلمة المرور."""
        repr_str = repr(admin_user)
        assert "password" not in repr_str.lower() or "hash" not in repr_str.lower()

    def test_disabled_user_cannot_access(self) -> None:
        """المستخدم المعطّل لا يملك صلاحيات."""
        user = User(
            id=uuid4(),
            username="disabled",
            email="d@e.com",
            password_hash="x",
            role=UserRole.ADMIN,
            status=UserStatus.DISABLED,
        )
        from domain.value_objects.value_objects import Permission
        assert not user.has_permission(Permission.USER_CREATE)
        assert not user.has_permission(Permission.CUSTOMER_VIEW)

    def test_locked_user_cannot_access(self) -> None:
        """المستخدم المقفل لا يملك صلاحيات."""
        user = User(
            id=uuid4(),
            username="locked",
            email="l@e.com",
            password_hash="x",
            role=UserRole.ADMIN,
            status=UserStatus.LOCKED,
        )
        from domain.value_objects.value_objects import Permission
        assert not user.has_permission(Permission.USER_CREATE)

    def test_accountant_cannot_delete_users(self) -> None:
        """المحاسب لا يمكنه حذف المستخدمين."""
        from domain.value_objects.value_objects import Permission, UserRole
        accountant = User(
            id=uuid4(), username="acc", email="a@e.com",
            password_hash="x", role=UserRole.ACCOUNTANT,
        )
        assert not accountant.has_permission(Permission.USER_DELETE)
        assert not accountant.has_permission(Permission.USER_CREATE)

    def test_owner_cannot_create_invoices(self) -> None:
        """صاحب الشركة لا يمكنه إنشاء فواتير (عرض فقط)."""
        from domain.value_objects.value_objects import Permission, UserRole
        owner = User(
            id=uuid4(), username="owner", email="o@e.com",
            password_hash="x", role=UserRole.COMPANY_OWNER,
        )
        assert not owner.has_permission(Permission.INVOICE_CREATE)
        assert owner.has_permission(Permission.INVOICE_VIEW)


class TestInvoiceNumberGeneration:
    """اختبارات توليد رقم الفاتورة."""

    @pytest.mark.asyncio
    async def test_invoice_no_unique(self, admin_user) -> None:
        """كل فاتورة تحصل على رقم فريد.

        ملاحظة: التوليد الحالي يعتمد على COUNT، لذا لو لم تُحفظ الفاتورة الأولى،
        قد يتكرر الرقم. الـ UNIQUE constraint في DB يمنع التكرار فعليًا.
        هذا الاختبار يتحقق من أن التوليد المتتالي (مع حفظ) يُولّد أرقامًا فريدة.
        """
        from domain.entities.invoice import Invoice, InvoiceStatus
        from decimal import Decimal
        from uuid import uuid4

        repo = SqlAlchemyInvoiceRepository()
        no1 = await repo.next_invoice_no(InvoiceType.SALE)
        # Create and save a real invoice to consume no1
        inv1 = Invoice(
            invoice_no=no1,
            invoice_type=InvoiceType.SALE,
            total=Decimal("100"),
            status=InvoiceStatus.POSTED,
            created_by=admin_user.id,
        )
        await repo.save(inv1)
        # Now next call should produce a different number
        no2 = await repo.next_invoice_no(InvoiceType.SALE)
        assert no1 != no2
        assert no1.startswith("INV-S-")
        assert no2.startswith("INV-S-")

    @pytest.mark.asyncio
    async def test_invoice_no_format(self) -> None:
        """صيغة رقم الفاتورة صحيحة: INV-S-YYYY-NNNNNN"""
        repo = SqlAlchemyInvoiceRepository()
        no = await repo.next_invoice_no(InvoiceType.PURCHASE)
        year = datetime.now().year
        assert no.startswith(f"INV-P-{year}-")
        assert len(no) > len(f"INV-P-{year}-")  # has sequence

    @pytest.mark.asyncio
    async def test_different_types_have_different_prefixes(self) -> None:
        """أنواع الفواتير المختلفة لها اختصارات مختلفة."""
        repo = SqlAlchemyInvoiceRepository()
        sale_no = await repo.next_invoice_no(InvoiceType.SALE)
        purchase_no = await repo.next_invoice_no(InvoiceType.PURCHASE)
        sale_return_no = await repo.next_invoice_no(InvoiceType.SALE_RETURN)
        purchase_return_no = await repo.next_invoice_no(InvoiceType.PURCHASE_RETURN)

        assert sale_no.startswith("INV-S-")
        assert purchase_no.startswith("INV-P-")
        assert sale_return_no.startswith("RET-S-")
        assert purchase_return_no.startswith("RET-P-")


class TestAtomicityIssues:
    """اختبارات للكشف عن مشاكل الـ Atomicity (موثقة كـ known issues)."""

    def test_uow_pattern_exists(self) -> None:
        """Unit of Work pattern مُعرَّف."""
        from infrastructure.db.unit_of_work import UnitOfWork, atomic_transaction
        assert UnitOfWork is not None
        assert atomic_transaction is not None

    def test_uow_rollback_on_exception(self) -> None:
        """UnitOfWork يُلغي التغييرات عند الاستثناء."""
        from infrastructure.db.unit_of_work import UnitOfWork
        from infrastructure.db.models.user_model import UserModel

        # Create a user, then trigger exception → should rollback
        initial_count = self._count_users()
        try:
            with UnitOfWork() as uow:
                new_user = UserModel(
                    id=str(uuid4()),
                    username="rollback_test",
                    email="rb@test.com",
                    password_hash="$2b$12$dummy",
                    full_name="Rollback Test",
                )
                uow.session.add(new_user)
                # Now raise an exception
                raise ValueError("Simulated failure")
        except ValueError:
            pass  # expected

        # Verify user was NOT saved
        new_count = self._count_users()
        assert new_count == initial_count, "UnitOfWork did not rollback!"

    def test_uow_commit_on_success(self) -> None:
        """UnitOfWork يحفظ التغييرات عند النجاح."""
        from infrastructure.db.unit_of_work import UnitOfWork
        from infrastructure.db.models.user_model import UserModel

        initial_count = self._count_users()
        test_id = str(uuid4())
        with UnitOfWork() as uow:
            new_user = UserModel(
                id=test_id,
                username="commit_test",
                email="ct@test.com",
                password_hash="$2b$12$dummy",
                full_name="Commit Test",
            )
            uow.session.add(new_user)

        new_count = self._count_users()
        assert new_count == initial_count + 1, "UnitOfWork did not commit!"

        # Cleanup
        with session_scope() as s:
            from sqlalchemy import delete
            s.execute(delete(UserModel).where(UserModel.id == test_id))

    def _count_users(self) -> int:
        from sqlalchemy import select, func
        with session_scope() as s:
            return s.execute(select(func.count(UserModel.id))).scalar() or 0


class TestCodeQuality:
    """اختبارات جودة الكود."""

    def test_no_hardcoded_secret_in_settings(self) -> None:
        """SECRET_KEY لها placeholder واضح (لا قيمة حقيقية)."""
        from infrastructure.config.settings import settings
        assert settings.SECRET_KEY == "change-me-in-production"

    def test_default_tax_rate_is_15(self) -> None:
        """نسبة الضريبة الافتراضية 15% (السعودية)."""
        from infrastructure.config.settings import settings
        assert settings.DEFAULT_TAX_RATE == 15.0

    def test_default_currency_is_sar(self) -> None:
        """العملة الافتراضية الريال السعودي."""
        from infrastructure.config.settings import settings
        assert settings.DEFAULT_CURRENCY == "SAR"

    def test_bcrypt_cost_factor_is_12(self) -> None:
        """عامل تكلفة bcrypt هو 12 (متوافق مع OWASP)."""
        from use_cases.auth.auth_use_cases import PasswordHasher
        assert PasswordHasher.BCRYPT_COST == 12

    def test_max_login_attempts_is_5(self) -> None:
        """الحد الأقصى لمحاولات الدخول الفاشلة 5."""
        from domain.entities.user import User
        assert User.MAX_FAILED_ATTEMPTS == 5

    def test_lock_duration_is_15_minutes(self) -> None:
        """مدة القفل 15 دقيقة."""
        from domain.entities.user import User
        assert User.LOCK_DURATION_MINUTES == 15
