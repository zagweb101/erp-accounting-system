"""
Customer Use Cases - حالات استخدام العملاء

CRUD كامل + بحث + تحديث الأرصدة.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from domain.entities.party import Customer
from domain.exceptions.exceptions import (
    CreditLimitExceededException,
    CustomerNotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from domain.value_objects.value_objects import Permission
from use_cases.repositories.interfaces import ICustomerRepository


# ============================================================
# DTOs
# ============================================================
@dataclass
class CreateCustomerRequest:
    code: str
    name: str
    name_en: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    tax_number: str = ""
    opening_balance: Decimal = Decimal("0")
    credit_limit: Decimal = Decimal("0")
    customer_category: str = "regular"
    payment_terms_days: int = 30
    notes: str = ""


@dataclass
class UpdateCustomerRequest:
    customer_id: UUID
    name: Optional[str] = None
    name_en: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_number: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    customer_category: Optional[str] = None
    payment_terms_days: Optional[int] = None
    notes: Optional[str] = None


@dataclass
class CustomerSearchRequest:
    query: str = ""
    limit: int = 10
    active_only: bool = True


# ============================================================
# Use Case: Create Customer
# ============================================================
class CreateCustomerUseCase:
    def __init__(self, customer_repo: ICustomerRepository) -> None:
        self._repo = customer_repo

    async def execute(self, request: CreateCustomerRequest, current_user) -> Customer:
        if not current_user.has_permission(Permission.CUSTOMER_CREATE):
            raise PermissionDeniedException("customer.create")

        # Validation
        if not request.code:
            raise ValidationException("code", "is required")
        if not request.name:
            raise ValidationException("name", "is required")
        if request.email and "@" not in request.email:
            raise ValidationException("email", "invalid format")
        if request.opening_balance < 0:
            raise ValidationException("opening_balance", "cannot be negative")
        if request.credit_limit < 0:
            raise ValidationException("credit_limit", "cannot be negative")
        if request.payment_terms_days < 0:
            raise ValidationException("payment_terms_days", "cannot be negative")

        # Check for duplicate code
        existing = await self._repo.get_by_code(request.code)
        if existing is not None:
            raise ValidationException("code", f"already exists: {request.code}")

        # Build entity
        customer = Customer(
            code=request.code,
            name=request.name,
            name_en=request.name_en,
            phone=request.phone,
            email=request.email,
            address=request.address,
            tax_number=request.tax_number,
            opening_balance=request.opening_balance,
            current_balance=request.opening_balance,  # initial = opening
            credit_limit=request.credit_limit,
            customer_category=request.customer_category,
            payment_terms_days=request.payment_terms_days,
            notes=request.notes,
            is_active=True,
        )
        return await self._repo.save(customer)


# ============================================================
# Use Case: Update Customer
# ============================================================
class UpdateCustomerUseCase:
    def __init__(self, customer_repo: ICustomerRepository) -> None:
        self._repo = customer_repo

    async def execute(self, request: UpdateCustomerRequest, current_user) -> Customer:
        if not current_user.has_permission(Permission.CUSTOMER_UPDATE):
            raise PermissionDeniedException("customer.update")

        customer = await self._repo.get_by_id(request.customer_id)
        if customer is None:
            raise CustomerNotFoundException(str(request.customer_id))

        # Apply partial updates
        if request.name is not None:
            if not request.name:
                raise ValidationException("name", "cannot be empty")
            customer.name = request.name
        if request.name_en is not None:
            customer.name_en = request.name_en
        if request.phone is not None:
            customer.phone = request.phone
        if request.email is not None:
            if request.email and "@" not in request.email:
                raise ValidationException("email", "invalid format")
            customer.email = request.email
        if request.address is not None:
            customer.address = request.address
        if request.tax_number is not None:
            customer.tax_number = request.tax_number
        if request.credit_limit is not None:
            if request.credit_limit < 0:
                raise ValidationException("credit_limit", "cannot be negative")
            customer.credit_limit = request.credit_limit
        if request.customer_category is not None:
            customer.customer_category = request.customer_category
        if request.payment_terms_days is not None:
            if request.payment_terms_days < 0:
                raise ValidationException("payment_terms_days", "cannot be negative")
            customer.payment_terms_days = request.payment_terms_days
        if request.notes is not None:
            customer.notes = request.notes

        from datetime import datetime
        customer.updated_at = datetime.now()
        return await self._repo.save(customer)


# ============================================================
# Use Case: Delete Customer (Soft delete)
# ============================================================
class DeleteCustomerUseCase:
    def __init__(self, customer_repo: ICustomerRepository) -> None:
        self._repo = customer_repo

    async def execute(self, customer_id: UUID, current_user) -> bool:
        if not current_user.has_permission(Permission.CUSTOMER_DELETE):
            raise PermissionDeniedException("customer.delete")

        customer = await self._repo.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundException(str(customer_id))

        # Rule: cannot delete if has balance
        if customer.current_balance > 0:
            raise ValidationException(
                "current_balance",
                f"cannot delete customer with positive balance: {customer.current_balance}",
            )

        # Soft delete: mark inactive
        customer.is_active = False
        from datetime import datetime
        customer.updated_at = datetime.now()
        await self._repo.save(customer)
        return True


# ============================================================
# Use Case: Get Customer
# ============================================================
class GetCustomerUseCase:
    def __init__(self, customer_repo: ICustomerRepository) -> None:
        self._repo = customer_repo

    async def execute(self, customer_id: UUID, current_user) -> Customer:
        if not current_user.has_permission(Permission.CUSTOMER_VIEW):
            raise PermissionDeniedException("customer.view")

        customer = await self._repo.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundException(str(customer_id))
        return customer


# ============================================================
# Use Case: List Customers
# ============================================================
class ListCustomersUseCase:
    def __init__(self, customer_repo: ICustomerRepository) -> None:
        self._repo = customer_repo

    async def execute(self, current_user, skip: int = 0, limit: int = 100) -> list[Customer]:
        if not current_user.has_permission(Permission.CUSTOMER_VIEW):
            raise PermissionDeniedException("customer.view")
        return await self._repo.list_all(skip=skip, limit=limit)


# ============================================================
# Use Case: Search Customers
# ============================================================
class SearchCustomersUseCase:
    def __init__(self, customer_repo: ICustomerRepository) -> None:
        self._repo = customer_repo

    async def execute(self, request: CustomerSearchRequest, current_user) -> list[Customer]:
        if not current_user.has_permission(Permission.CUSTOMER_VIEW):
            raise PermissionDeniedException("customer.view")
        if not request.query or len(request.query) < 2:
            return []
        return await self._repo.search(request.query, limit=request.limit)


# ============================================================
# Use Case: Check Credit Limit (helper for invoice use cases)
# ============================================================
class CheckCreditLimitUseCase:
    """التحقق من حد الائتمان قبل إنشاء فاتورة آجلة."""

    def __init__(self, customer_repo: ICustomerRepository) -> None:
        self._repo = customer_repo

    async def execute(
        self, customer_id: UUID, additional_amount: Decimal
    ) -> tuple[bool, str]:
        """يُعيد (allowed, reason)."""
        customer = await self._repo.get_by_id(customer_id)
        if customer is None:
            return False, "العميل غير موجود"
        if not customer.is_within_credit_limit(additional_amount):
            raise CreditLimitExceededException(
                customer.name,
                float(customer.credit_limit),
                float(customer.current_balance + additional_amount),
            )
        return True, "OK"
