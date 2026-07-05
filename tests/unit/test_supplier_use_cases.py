"""
اختبارات شاملة لـ Supplier Use Cases (رفع التغطية من 52% إلى 80%+)
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

from adapters.repositories.sql_alchemy.user_repository import SqlAlchemyUserRepository
from adapters.repositories.sql_alchemy.party_repository import SqlAlchemySupplierRepository
from use_cases.suppliers.supplier_use_cases import (
    CreateSupplierRequest, CreateSupplierUseCase,
    UpdateSupplierRequest, UpdateSupplierUseCase,
    DeleteSupplierUseCase, GetSupplierUseCase, ListSuppliersUseCase,
)
from domain.entities.user import User, UserStatus
from domain.value_objects.value_objects import UserRole
from domain.exceptions.exceptions import (
    PermissionDeniedException, SupplierNotFoundException, ValidationException,
)


@pytest.fixture
def repo():
    return SqlAlchemySupplierRepository()


@pytest.fixture
def admin_user():
    from sqlalchemy import select
    with session_scope() as s:
        m = s.execute(select(UserModel).where(UserModel.username == "admin")).scalar_one()
        return User(
            id=m.id, username=m.username, email=m.email, password_hash=m.password_hash,
            full_name=m.full_name, role=UserRole(m.role), status=UserStatus(m.status),
        )


class TestCreateSupplierUseCase:
    """اختبارات إنشاء الموردين."""

    @pytest.mark.asyncio
    async def test_create_supplier_success(self, repo, admin_user):
        """إنشاء مورد جديد بنجاح."""
        uc = CreateSupplierUseCase(repo)
        supplier = await uc.execute(
            CreateSupplierRequest(
                code=f"S-TEST-{uuid4().hex[:8]}",
                name="مورد الاختبار",
                phone="0501234567",
                email=f"supplier_{uuid4().hex[:8]}@test.com",
                address="الرياض",
                tax_number="300000000000003",
                opening_balance=Decimal("2000"),
                credit_limit=Decimal("100000"),
            ),
            current_user=admin_user,
        )
        assert supplier.code.startswith("S-TEST-")
        assert supplier.name == "مورد الاختبار"
        assert supplier.current_balance == Decimal("2000")
        assert supplier.credit_limit == Decimal("100000")

    @pytest.mark.asyncio
    async def test_create_supplier_duplicate_code(self, repo, admin_user):
        """كود مورد مكرر يفشل."""
        uc = CreateSupplierUseCase(repo)
        code = f"S-DUP-{uuid4().hex[:8]}"
        await uc.execute(
            CreateSupplierRequest(code=code, name="Supplier 1"),
            current_user=admin_user,
        )
        with pytest.raises(ValidationException, match="already exists"):
            await uc.execute(
                CreateSupplierRequest(code=code, name="Supplier 2"),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_supplier_empty_code(self, repo, admin_user):
        """كود فارغ يفشل."""
        uc = CreateSupplierUseCase(repo)
        with pytest.raises(ValidationException, match="is required"):
            await uc.execute(
                CreateSupplierRequest(code="", name="Test"),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_supplier_empty_name(self, repo, admin_user):
        """اسم فارغ يفشل."""
        uc = CreateSupplierUseCase(repo)
        with pytest.raises(ValidationException, match="is required"):
            await uc.execute(
                CreateSupplierRequest(code=f"S-{uuid4().hex[:8]}", name=""),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_supplier_invalid_email(self, repo, admin_user):
        """بريد إلكتروني غير صالح يفشل."""
        uc = CreateSupplierUseCase(repo)
        with pytest.raises(ValidationException, match="invalid"):
            await uc.execute(
                CreateSupplierRequest(
                    code=f"S-{uuid4().hex[:8]}",
                    name="Test",
                    email="invalid-email",
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_supplier_negative_balance(self, repo, admin_user):
        """رصيد افتتاحي سالب يفشل."""
        uc = CreateSupplierUseCase(repo)
        with pytest.raises(ValidationException, match="negative"):
            await uc.execute(
                CreateSupplierRequest(
                    code=f"S-{uuid4().hex[:8]}",
                    name="Test",
                    opening_balance=Decimal("-100"),
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_supplier_by_accountant_succeeds(self, repo, admin_user):
        """المحاسب يمكنه إنشاء موردين."""
        from use_cases.auth.auth_use_cases import CreateUserUseCase, CreateUserRequest
        from domain.value_objects.value_objects import UserRole

        # Create accountant
        create_user_uc = CreateUserUseCase(SqlAlchemyUserRepository())
        accountant = await create_user_uc.execute(
            CreateUserRequest(
                username=f"acc_supplier_{uuid4().hex[:8]}",
                password="Pass@123",
                email=f"acc_s_{uuid4().hex[:8]}@test.com",
                full_name="Test Accountant",
                role=UserRole.ACCOUNTANT,
            ),
            current_user=admin_user,
        )

        uc = CreateSupplierUseCase(repo)
        supplier = await uc.execute(
            CreateSupplierRequest(code=f"S-ACC-{uuid4().hex[:8]}", name="By Accountant"),
            current_user=accountant,
        )
        assert supplier.name == "By Accountant"

    @pytest.mark.asyncio
    async def test_create_supplier_by_inventory_clerk_fails(self, repo, admin_user):
        """موظف المخزون لا يمكنه إنشاء موردين."""
        from use_cases.auth.auth_use_cases import CreateUserUseCase, CreateUserRequest
        from domain.value_objects.value_objects import UserRole

        create_user_uc = CreateUserUseCase(SqlAlchemyUserRepository())
        clerk = await create_user_uc.execute(
            CreateUserRequest(
                username=f"clerk_supplier_{uuid4().hex[:8]}",
                password="Pass@123",
                email=f"clerk_s_{uuid4().hex[:8]}@test.com",
                full_name="Test Clerk",
                role=UserRole.INVENTORY_CLERK,
            ),
            current_user=admin_user,
        )

        uc = CreateSupplierUseCase(repo)
        with pytest.raises(PermissionDeniedException):
            await uc.execute(
                CreateSupplierRequest(code=f"S-CLK-{uuid4().hex[:8]}", name="By Clerk"),
                current_user=clerk,
            )


class TestUpdateSupplierUseCase:
    """اختبارات تحديث الموردين."""

    @pytest.mark.asyncio
    async def test_update_supplier_name(self, repo, admin_user):
        """تحديث اسم المورد."""
        create_uc = CreateSupplierUseCase(repo)
        supplier = await create_uc.execute(
            CreateSupplierRequest(code=f"S-UPD-{uuid4().hex[:8]}", name="Original"),
            current_user=admin_user,
        )

        update_uc = UpdateSupplierUseCase(repo)
        updated = await update_uc.execute(
            UpdateSupplierRequest(supplier_id=supplier.id, name="Updated Name"),
            current_user=admin_user,
        )
        assert updated.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_supplier_phone_email(self, repo, admin_user):
        """تحديث الهاتف والبريد."""
        create_uc = CreateSupplierUseCase(repo)
        supplier = await create_uc.execute(
            CreateSupplierRequest(code=f"S-CON-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )

        update_uc = UpdateSupplierUseCase(repo)
        updated = await update_uc.execute(
            UpdateSupplierRequest(
                supplier_id=supplier.id,
                phone="0555555555",
                email=f"updated_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )
        assert updated.phone == "0555555555"
        assert "updated_" in updated.email

    @pytest.mark.asyncio
    async def test_update_supplier_credit_limit(self, repo, admin_user):
        """تحديث حد الائتمان."""
        create_uc = CreateSupplierUseCase(repo)
        supplier = await create_uc.execute(
            CreateSupplierRequest(code=f"S-CL-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )

        update_uc = UpdateSupplierUseCase(repo)
        updated = await update_uc.execute(
            UpdateSupplierRequest(
                supplier_id=supplier.id,
                credit_limit=Decimal("50000"),
            ),
            current_user=admin_user,
        )
        assert updated.credit_limit == Decimal("50000")

    @pytest.mark.asyncio
    async def test_update_supplier_payment_terms(self, repo, admin_user):
        """تحديث آجل السداد."""
        create_uc = CreateSupplierUseCase(repo)
        supplier = await create_uc.execute(
            CreateSupplierRequest(code=f"S-PT-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )

        update_uc = UpdateSupplierUseCase(repo)
        updated = await update_uc.execute(
            UpdateSupplierRequest(
                supplier_id=supplier.id,
                payment_terms_days=60,
            ),
            current_user=admin_user,
        )
        assert updated.payment_terms_days == 60

    @pytest.mark.asyncio
    async def test_update_supplier_empty_name_fails(self, repo, admin_user):
        """تحديث الاسم لقيمة فارغة يفشل."""
        create_uc = CreateSupplierUseCase(repo)
        supplier = await create_uc.execute(
            CreateSupplierRequest(code=f"S-EN-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )

        update_uc = UpdateSupplierUseCase(repo)
        with pytest.raises(ValidationException, match="cannot be empty"):
            await update_uc.execute(
                UpdateSupplierRequest(supplier_id=supplier.id, name=""),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_update_nonexistent_supplier(self, repo, admin_user):
        """تحديث مورد غير موجود يفشل."""
        update_uc = UpdateSupplierUseCase(repo)
        with pytest.raises(SupplierNotFoundException):
            await update_uc.execute(
                UpdateSupplierRequest(supplier_id=uuid4(), name="Test"),
                current_user=admin_user,
            )


class TestDeleteSupplierUseCase:
    """اختبارات حذف الموردين."""

    @pytest.mark.asyncio
    async def test_delete_supplier_success(self, repo, admin_user):
        """حذف مورد بدون رصيد ينجح."""
        create_uc = CreateSupplierUseCase(repo)
        supplier = await create_uc.execute(
            CreateSupplierRequest(code=f"S-DEL-{uuid4().hex[:8]}", name="To Delete"),
            current_user=admin_user,
        )

        delete_uc = DeleteSupplierUseCase(repo)
        result = await delete_uc.execute(supplier.id, current_user=admin_user)
        assert result is True

        # Verify soft delete (is_active = False)
        fetched = await repo.get_by_id(supplier.id)
        assert fetched.is_active is False

    @pytest.mark.asyncio
    async def test_delete_supplier_with_balance_fails(self, repo, admin_user):
        """حذف مورد له رصيد يفشل."""
        create_uc = CreateSupplierUseCase(repo)
        supplier = await create_uc.execute(
            CreateSupplierRequest(
                code=f"S-DB-{uuid4().hex[:8]}",
                name="Has Balance",
                opening_balance=Decimal("1000"),
            ),
            current_user=admin_user,
        )

        delete_uc = DeleteSupplierUseCase(repo)
        with pytest.raises(ValidationException, match="positive balance"):
            await delete_uc.execute(supplier.id, current_user=admin_user)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_supplier(self, repo, admin_user):
        """حذف مورد غير موجود يفشل."""
        delete_uc = DeleteSupplierUseCase(repo)
        with pytest.raises(SupplierNotFoundException):
            await delete_uc.execute(uuid4(), current_user=admin_user)


class TestGetSupplierUseCase:
    """اختبارات الحصول على مورد."""

    @pytest.mark.asyncio
    async def test_get_supplier_success(self, repo, admin_user):
        """الحصول على مورد موجود ينجح."""
        create_uc = CreateSupplierUseCase(repo)
        supplier = await create_uc.execute(
            CreateSupplierRequest(code=f"S-GET-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )

        get_uc = GetSupplierUseCase(repo)
        fetched = await get_uc.execute(supplier.id, current_user=admin_user)
        assert fetched.id == supplier.id
        assert fetched.name == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_supplier(self, repo, admin_user):
        """الحصول على مورد غير موجود يفشل."""
        get_uc = GetSupplierUseCase(repo)
        with pytest.raises(SupplierNotFoundException):
            await get_uc.execute(uuid4(), current_user=admin_user)


class TestListSuppliersUseCase:
    """اختبارات سرد الموردين."""

    @pytest.mark.asyncio
    async def test_list_suppliers(self, repo, admin_user):
        """سرد الموردين يُعيد قائمة."""
        list_uc = ListSuppliersUseCase(repo)
        suppliers = await list_uc.execute(current_user=admin_user)
        assert isinstance(suppliers, list)

    @pytest.mark.asyncio
    async def test_list_suppliers_pagination(self, repo, admin_user):
        """سرد الموردين مع pagination."""
        create_uc = CreateSupplierUseCase(repo)
        for i in range(5):
            await create_uc.execute(
                CreateSupplierRequest(
                    code=f"S-PG-{i}-{uuid4().hex[:8]}",
                    name=f"Supplier {i}",
                ),
                current_user=admin_user,
            )

        list_uc = ListSuppliersUseCase(repo)
        first_page = await list_uc.execute(current_user=admin_user, skip=0, limit=3)
        assert len(first_page) <= 3

    @pytest.mark.asyncio
    async def test_list_suppliers_returns_domain_entities(self, repo, admin_user):
        """list يُعيد Domain entities."""
        list_uc = ListSuppliersUseCase(repo)
        suppliers = await list_uc.execute(current_user=admin_user)
        for s in suppliers:
            from domain.entities.party import Supplier
            assert isinstance(s, Supplier)
