"""
Supplier Use Cases - حالات استخدام الموردين

مشابه للعملاء لكن للموردين.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from domain.entities.party import Supplier
from domain.exceptions.exceptions import (
    PermissionDeniedException,
    SupplierNotFoundException,
    ValidationException,
)
from domain.value_objects.value_objects import Permission
from use_cases.repositories.interfaces import ISupplierRepository


@dataclass
class CreateSupplierRequest:
    code: str
    name: str
    name_en: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    tax_number: str = ""
    opening_balance: Decimal = Decimal("0")
    credit_limit: Decimal = Decimal("0")
    supplier_category: str = "regular"
    payment_terms_days: int = 30
    notes: str = ""


@dataclass
class UpdateSupplierRequest:
    supplier_id: UUID
    name: Optional[str] = None
    name_en: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_number: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    supplier_category: Optional[str] = None
    payment_terms_days: Optional[int] = None
    notes: Optional[str] = None


class CreateSupplierUseCase:
    def __init__(self, supplier_repo: ISupplierRepository) -> None:
        self._repo = supplier_repo

    async def execute(self, request: CreateSupplierRequest, current_user) -> Supplier:
        if not current_user.has_permission(Permission.SUPPLIER_CREATE):
            raise PermissionDeniedException("supplier.create")
        if not request.code:
            raise ValidationException("code", "is required")
        if not request.name:
            raise ValidationException("name", "is required")
        if request.email and "@" not in request.email:
            raise ValidationException("email", "invalid format")
        if request.opening_balance < 0:
            raise ValidationException("opening_balance", "cannot be negative")

        existing = await self._repo.get_by_code(request.code)
        if existing is not None:
            raise ValidationException("code", f"already exists: {request.code}")

        supplier = Supplier(
            code=request.code,
            name=request.name,
            name_en=request.name_en,
            phone=request.phone,
            email=request.email,
            address=request.address,
            tax_number=request.tax_number,
            opening_balance=request.opening_balance,
            current_balance=request.opening_balance,
            credit_limit=request.credit_limit,
            supplier_category=request.supplier_category,
            payment_terms_days=request.payment_terms_days,
            notes=request.notes,
            is_active=True,
        )
        return await self._repo.save(supplier)


class UpdateSupplierUseCase:
    def __init__(self, supplier_repo: ISupplierRepository) -> None:
        self._repo = supplier_repo

    async def execute(self, request: UpdateSupplierRequest, current_user) -> Supplier:
        if not current_user.has_permission(Permission.SUPPLIER_UPDATE):
            raise PermissionDeniedException("supplier.update")

        supplier = await self._repo.get_by_id(request.supplier_id)
        if supplier is None:
            raise SupplierNotFoundException(str(request.supplier_id))

        if request.name is not None:
            if not request.name:
                raise ValidationException("name", "cannot be empty")
            supplier.name = request.name
        if request.phone is not None:
            supplier.phone = request.phone
        if request.email is not None:
            supplier.email = request.email
        if request.address is not None:
            supplier.address = request.address
        if request.tax_number is not None:
            supplier.tax_number = request.tax_number
        if request.credit_limit is not None:
            supplier.credit_limit = request.credit_limit
        if request.supplier_category is not None:
            supplier.supplier_category = request.supplier_category
        if request.payment_terms_days is not None:
            supplier.payment_terms_days = request.payment_terms_days
        if request.notes is not None:
            supplier.notes = request.notes

        from datetime import datetime
        supplier.updated_at = datetime.now()
        return await self._repo.save(supplier)


class DeleteSupplierUseCase:
    def __init__(self, supplier_repo: ISupplierRepository) -> None:
        self._repo = supplier_repo

    async def execute(self, supplier_id: UUID, current_user) -> bool:
        if not current_user.has_permission(Permission.SUPPLIER_DELETE):
            raise PermissionDeniedException("supplier.delete")

        supplier = await self._repo.get_by_id(supplier_id)
        if supplier is None:
            raise SupplierNotFoundException(str(supplier_id))

        if supplier.current_balance > 0:
            raise ValidationException(
                "current_balance",
                f"cannot delete supplier with positive balance: {supplier.current_balance}",
            )

        supplier.is_active = False
        from datetime import datetime
        supplier.updated_at = datetime.now()
        await self._repo.save(supplier)
        return True


class GetSupplierUseCase:
    def __init__(self, supplier_repo: ISupplierRepository) -> None:
        self._repo = supplier_repo

    async def execute(self, supplier_id: UUID, current_user) -> Supplier:
        if not current_user.has_permission(Permission.SUPPLIER_VIEW):
            raise PermissionDeniedException("supplier.view")
        supplier = await self._repo.get_by_id(supplier_id)
        if supplier is None:
            raise SupplierNotFoundException(str(supplier_id))
        return supplier


class ListSuppliersUseCase:
    def __init__(self, supplier_repo: ISupplierRepository) -> None:
        self._repo = supplier_repo

    async def execute(self, current_user, skip: int = 0, limit: int = 100) -> list[Supplier]:
        if not current_user.has_permission(Permission.SUPPLIER_VIEW):
            raise PermissionDeniedException("supplier.view")
        return await self._repo.list_all(skip=skip, limit=limit)
