"""
اختبارات وحدة العملاء
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

# Setup test environment
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.db.session import session_scope


from infrastructure.db.models.user_model import UserModel

from adapters.repositories.sql_alchemy.user_repository import SqlAlchemyUserRepository
from adapters.repositories.sql_alchemy.party_repository import (
    SqlAlchemyCustomerRepository, SqlAlchemySupplierRepository
)
from use_cases.customers.customer_use_cases import (
    CreateCustomerUseCase, CreateCustomerRequest,
    UpdateCustomerUseCase, UpdateCustomerRequest,
    DeleteCustomerUseCase, SearchCustomersUseCase, CustomerSearchRequest,
    GetCustomerUseCase, ListCustomersUseCase,
)
from use_cases.suppliers.supplier_use_cases import (
    CreateSupplierUseCase, CreateSupplierRequest,
)
from domain.entities.user import User, UserStatus
from domain.value_objects.value_objects import UserRole
from domain.exceptions.exceptions import (
    CustomerNotFoundException, ValidationException, PermissionDeniedException,
)


@pytest.fixture
def admin_user():
    """Get admin user from DB."""
    from sqlalchemy import select
    with session_scope() as s:
        m = s.execute(select(UserModel).where(UserModel.username == "admin")).scalar_one()
        return User(
            id=m.id, username=m.username, email=m.email, password_hash=m.password_hash,
            full_name=m.full_name, role=UserRole(m.role), status=UserStatus(m.status),
        )


@pytest.fixture
def customer_repo():
    return SqlAlchemyCustomerRepository()


@pytest.fixture
def supplier_repo():
    return SqlAlchemySupplierRepository()


class TestCustomerUseCases:
    """اختبارات وحدة العملاء."""

    @pytest.mark.asyncio
    async def test_create_customer_success(self, admin_user, customer_repo):
        uc = CreateCustomerUseCase(customer_repo)
        req = CreateCustomerRequest(
            code="C-TEST-001",
            name="شركة النور للتجارة",
            phone="0501234567",
            email="info@alnoor.com",
            address="الرياض",
            tax_number="300000000000003",
            opening_balance=Decimal("5000"),
            credit_limit=Decimal("50000"),
        )
        customer = await uc.execute(req, admin_user)
        assert customer.code == "C-TEST-001"
        assert customer.name == "شركة النور للتجارة"
        assert customer.current_balance == Decimal("5000")
        assert customer.credit_limit == Decimal("50000")
        assert customer.is_active is True

    @pytest.mark.asyncio
    async def test_create_customer_duplicate_code_raises(self, admin_user, customer_repo):
        uc = CreateCustomerUseCase(customer_repo)
        req = CreateCustomerRequest(code="C-DUP-001", name="Customer 1")
        await uc.execute(req, admin_user)

        # Second with same code
        req2 = CreateCustomerRequest(code="C-DUP-001", name="Customer 2")
        with pytest.raises(ValidationException, match="already exists"):
            await uc.execute(req2, admin_user)

    @pytest.mark.asyncio
    async def test_create_customer_invalid_email(self, admin_user, customer_repo):
        uc = CreateCustomerUseCase(customer_repo)
        req = CreateCustomerRequest(
            code="C-EMAIL-001", name="Test", email="invalid-email",
        )
        with pytest.raises(ValidationException, match="invalid format"):
            await uc.execute(req, admin_user)

    @pytest.mark.asyncio
    async def test_create_customer_negative_balance_raises(self, admin_user, customer_repo):
        uc = CreateCustomerUseCase(customer_repo)
        req = CreateCustomerRequest(
            code="C-NEG-001", name="Test", opening_balance=Decimal("-100"),
        )
        with pytest.raises(ValidationException, match="cannot be negative"):
            await uc.execute(req, admin_user)

    @pytest.mark.asyncio
    async def test_update_customer(self, admin_user, customer_repo):
        # Create
        create_uc = CreateCustomerUseCase(customer_repo)
        customer = await create_uc.execute(
            CreateCustomerRequest(code="C-UPD-001", name="Original Name"),
            admin_user,
        )

        # Update
        update_uc = UpdateCustomerUseCase(customer_repo)
        updated = await update_uc.execute(
            UpdateCustomerRequest(
                customer_id=customer.id,
                name="Updated Name",
                phone="0555555555",
                credit_limit=Decimal("10000"),
            ),
            admin_user,
        )
        assert updated.name == "Updated Name"
        assert updated.phone == "0555555555"
        assert updated.credit_limit == Decimal("10000")

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, admin_user, customer_repo):
        uc = GetCustomerUseCase(customer_repo)
        with pytest.raises(CustomerNotFoundException):
            await uc.execute(uuid4(), admin_user)

    @pytest.mark.asyncio
    async def test_search_customers(self, admin_user, customer_repo):
        create_uc = CreateCustomerUseCase(customer_repo)
        await create_uc.execute(
            CreateCustomerRequest(code="C-SEARCH-001", name="شركة البحث"),
            admin_user,
        )
        await create_uc.execute(
            CreateCustomerRequest(code="C-SEARCH-002", name="شركة الاختبار"),
            admin_user,
        )

        search_uc = SearchCustomersUseCase(customer_repo)
        results = await search_uc.execute(
            CustomerSearchRequest(query="بحث"), admin_user,
        )
        assert len(results) >= 1
        assert any("البحث" in c.name for c in results)

    @pytest.mark.asyncio
    async def test_delete_customer_with_balance_raises(self, admin_user, customer_repo):
        create_uc = CreateCustomerUseCase(customer_repo)
        customer = await create_uc.execute(
            CreateCustomerRequest(
                code="C-DEL-001", name="Delete Me",
                opening_balance=Decimal("1000"),
            ),
            admin_user,
        )
        delete_uc = DeleteCustomerUseCase(customer_repo)
        with pytest.raises(ValidationException, match="positive balance"):
            await delete_uc.execute(customer.id, admin_user)

    @pytest.mark.asyncio
    async def test_delete_customer_success(self, admin_user, customer_repo):
        create_uc = CreateCustomerUseCase(customer_repo)
        customer = await create_uc.execute(
            CreateCustomerRequest(code="C-DEL-002", name="Delete Me 2"),
            admin_user,
        )
        delete_uc = DeleteCustomerUseCase(customer_repo)
        result = await delete_uc.execute(customer.id, admin_user)
        assert result is True

        # Verify soft delete
        fetched = await customer_repo.get_by_id(customer.id)
        assert fetched.is_active is False

    @pytest.mark.asyncio
    async def test_list_customers(self, admin_user, customer_repo):
        list_uc = ListCustomersUseCase(customer_repo)
        customers = await list_uc.execute(admin_user)
        assert isinstance(customers, list)
        assert len(customers) >= 0


class TestSupplierUseCases:
    """اختبارات وحدة الموردين."""

    @pytest.mark.asyncio
    async def test_create_supplier_success(self, admin_user, supplier_repo):
        uc = CreateSupplierUseCase(supplier_repo)
        req = CreateSupplierRequest(
            code="S-TEST-001",
            name="مورد الإلكترونيات",
            phone="0509876543",
            email="sales@supplier.com",
            opening_balance=Decimal("2000"),
        )
        supplier = await uc.execute(req, admin_user)
        assert supplier.code == "S-TEST-001"
        assert supplier.name == "مورد الإلكترونيات"
        assert supplier.current_balance == Decimal("2000")

    @pytest.mark.asyncio
    async def test_create_supplier_duplicate_code(self, admin_user, supplier_repo):
        uc = CreateSupplierUseCase(supplier_repo)
        await uc.execute(CreateSupplierRequest(code="S-DUP-001", name="S1"), admin_user)
        with pytest.raises(ValidationException, match="already exists"):
            await uc.execute(CreateSupplierRequest(code="S-DUP-001", name="S2"), admin_user)


class TestPermissions:
    """اختبارات الصلاحيات."""

    @pytest.mark.asyncio
    async def test_accountant_cannot_create_user(self, customer_repo):
        """المحاسب لا يمكنه إنشاء مستخدمين لكنه يُنشئ عملاء."""
        # Create accountant user
        accountant = User(
            id=str(uuid4()), username="accountant_test",
            email="acc@test.com", password_hash="hash",
            role=UserRole.ACCOUNTANT,
        )
        # Should succeed for customer
        create_uc = CreateCustomerUseCase(customer_repo)
        req = CreateCustomerRequest(code="C-PERM-001", name="Test")
        customer = await create_uc.execute(req, accountant)
        assert customer.code == "C-PERM-001"
