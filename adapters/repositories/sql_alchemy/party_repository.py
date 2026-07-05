"""
SQLAlchemy Customer & Supplier Repository Implementations

يدعم وضعين:
1. وضع مستقل (default): كل دالة تفتح session_scope() خاصًا بها
2. وضع UnitOfWork: يمكن تمرير session خارجية للعمل ضمن معاملة ذرية
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from domain.entities.party import Customer, Supplier
from infrastructure.db.models.party_model import CustomerModel, SupplierModel
from infrastructure.db.session import session_scope
from use_cases.repositories.interfaces import ICustomerRepository, ISupplierRepository


# ============================================================
# Customer Repository
# ============================================================
class SqlAlchemyCustomerRepository(ICustomerRepository):
    def _to_entity(self, m: CustomerModel) -> Customer:
        """ To Entity."""
        return Customer(
            id=UUID(m.id),
            code=m.code,
            name=m.name,
            name_en=m.name_en,
            phone=m.phone,
            email=m.email,
            address=m.address,
            tax_number=m.tax_number,
            opening_balance=Decimal(str(m.opening_balance)),
            current_balance=Decimal(str(m.current_balance)),
            credit_limit=Decimal(str(m.credit_limit)),
            customer_category=m.customer_category,
            payment_terms_days=m.payment_terms_days,
            notes=m.notes,
            is_active=m.is_active,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def _to_model(self, e: Customer, m: CustomerModel | None = None) -> CustomerModel:
        """ To Model."""
        if m is None:
            m = CustomerModel(id=str(e.id))
        m.code = e.code
        m.name = e.name
        m.name_en = e.name_en
        m.phone = e.phone
        m.email = e.email
        m.address = e.address
        m.tax_number = e.tax_number
        m.opening_balance = e.opening_balance
        m.current_balance = e.current_balance
        m.credit_limit = e.credit_limit
        m.customer_category = e.customer_category
        m.payment_terms_days = e.payment_terms_days
        m.notes = e.notes
        m.is_active = e.is_active
        m.updated_at = e.updated_at
        return m

    async def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        with session_scope() as s:
            m = s.execute(
                select(CustomerModel).where(CustomerModel.id == str(customer_id))
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def get_by_code(self, code: str) -> Optional[Customer]:
        with session_scope() as s:
            m = s.execute(
                select(CustomerModel).where(CustomerModel.code == code)
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def save(self, customer: Customer) -> Customer:
        """حفظ العميل في معاملة مستقلة."""
        with session_scope() as s:
            return await self._save_in_session(customer, s)

    async def _save_in_session(self, customer: Customer, session: Session) -> Customer:
        """حفظ العميل في session موجودة (للـ UnitOfWork)."""
        existing = session.execute(
            select(CustomerModel).where(CustomerModel.id == str(customer.id))
        ).scalar_one_or_none()
        m = self._to_model(customer, existing)
        session.add(m)
        session.flush()
        session.refresh(m)
        return self._to_entity(m)

    async def delete(self, customer_id: UUID) -> bool:
        # Soft delete is handled in use case; physical delete here if needed
        with session_scope() as s:
            m = s.execute(
                select(CustomerModel).where(CustomerModel.id == str(customer_id))
            ).scalar_one_or_none()
            if m is None:
                return False
            s.delete(m)
            return True

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Customer]:
        with session_scope() as s:
            stmt = (
                select(CustomerModel)
                .order_by(CustomerModel.code)
                .offset(skip)
                .limit(limit)
            )
            models = s.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]

    async def search(self, query: str, limit: int = 10) -> list[Customer]:
        with session_scope() as s:
            pattern = f"%{query}%"
            stmt = (
                select(CustomerModel)
                .where(
                    or_(
                        CustomerModel.name.ilike(pattern),
                        CustomerModel.code.ilike(pattern),
                        CustomerModel.phone.ilike(pattern),
                        CustomerModel.email.ilike(pattern),
                    )
                )
                .order_by(CustomerModel.name)
                .limit(limit)
            )
            models = s.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]


# ============================================================
# Supplier Repository
# ============================================================
class SqlAlchemySupplierRepository(ISupplierRepository):
    def _to_entity(self, m: SupplierModel) -> Supplier:
        """ To Entity."""
        return Supplier(
            id=UUID(m.id),
            code=m.code,
            name=m.name,
            name_en=m.name_en,
            phone=m.phone,
            email=m.email,
            address=m.address,
            tax_number=m.tax_number,
            opening_balance=Decimal(str(m.opening_balance)),
            current_balance=Decimal(str(m.current_balance)),
            credit_limit=Decimal(str(m.credit_limit)),
            supplier_category=m.supplier_category,
            payment_terms_days=m.payment_terms_days,
            notes=m.notes,
            is_active=m.is_active,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def _to_model(self, e: Supplier, m: SupplierModel | None = None) -> SupplierModel:
        """ To Model."""
        if m is None:
            m = SupplierModel(id=str(e.id))
        m.code = e.code
        m.name = e.name
        m.name_en = e.name_en
        m.phone = e.phone
        m.email = e.email
        m.address = e.address
        m.tax_number = e.tax_number
        m.opening_balance = e.opening_balance
        m.current_balance = e.current_balance
        m.credit_limit = e.credit_limit
        m.supplier_category = e.supplier_category
        m.payment_terms_days = e.payment_terms_days
        m.notes = e.notes
        m.is_active = e.is_active
        m.updated_at = e.updated_at
        return m

    async def get_by_id(self, supplier_id: UUID) -> Optional[Supplier]:
        with session_scope() as s:
            m = s.execute(
                select(SupplierModel).where(SupplierModel.id == str(supplier_id))
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def get_by_code(self, code: str) -> Optional[Supplier]:
        with session_scope() as s:
            m = s.execute(
                select(SupplierModel).where(SupplierModel.code == code)
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def save(self, supplier: Supplier) -> Supplier:
        """حفظ المورد في معاملة مستقلة."""
        with session_scope() as s:
            return await self._save_in_session(supplier, s)

    async def _save_in_session(self, supplier: Supplier, session: Session) -> Supplier:
        """حفظ المورد في session موجودة (للـ UnitOfWork)."""
        existing = session.execute(
            select(SupplierModel).where(SupplierModel.id == str(supplier.id))
        ).scalar_one_or_none()
        m = self._to_model(supplier, existing)
        session.add(m)
        session.flush()
        session.refresh(m)
        return self._to_entity(m)

    async def delete(self, supplier_id: UUID) -> bool:
        with session_scope() as s:
            m = s.execute(
                select(SupplierModel).where(SupplierModel.id == str(supplier_id))
            ).scalar_one_or_none()
            if m is None:
                return False
            s.delete(m)
            return True

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Supplier]:
        with session_scope() as s:
            stmt = (
                select(SupplierModel)
                .order_by(SupplierModel.code)
                .offset(skip)
                .limit(limit)
            )
            models = s.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]
