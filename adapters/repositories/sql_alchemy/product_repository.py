"""
SQLAlchemy Product & Inventory Repository Implementations
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session

from domain.entities.product import InventoryEntry, Product
from infrastructure.db.models.product_model import InventoryEntryModel, ProductModel
from infrastructure.db.session import session_scope
from use_cases.repositories.interfaces import IInventoryRepository, IProductRepository


class SqlAlchemyProductRepository(IProductRepository):
    def _to_entity(self, m: ProductModel) -> Product:
        """ To Entity."""
        return Product(
            id=UUID(m.id),
            sku=m.sku,
            barcode=m.barcode,
            name=m.name,
            name_en=m.name_en,
            description=m.description,
            category=m.category,
            unit=m.unit,
            cost_price=Decimal(str(m.cost_price)),
            sale_price=Decimal(str(m.sale_price)),
            tax_rate=Decimal(str(m.tax_rate)),
            min_stock_level=Decimal(str(m.min_stock_level)),
            is_active=m.is_active,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def _to_model(self, e: Product, m: ProductModel | None = None) -> ProductModel:
        """ To Model."""
        if m is None:
            m = ProductModel(id=str(e.id))
        m.sku = e.sku
        m.barcode = e.barcode
        m.name = e.name
        m.name_en = e.name_en
        m.description = e.description
        m.category = e.category
        m.unit = e.unit
        m.cost_price = e.cost_price
        m.sale_price = e.sale_price
        m.tax_rate = e.tax_rate
        m.min_stock_level = e.min_stock_level
        m.is_active = e.is_active
        m.updated_at = e.updated_at
        return m

    async def get_by_id(self, product_id: UUID) -> Optional[Product]:
        with session_scope() as s:
            m = s.execute(
                select(ProductModel).where(ProductModel.id == str(product_id))
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def get_by_sku(self, sku: str) -> Optional[Product]:
        with session_scope() as s:
            m = s.execute(
                select(ProductModel).where(ProductModel.sku == sku)
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def get_by_barcode(self, barcode: str) -> Optional[Product]:
        with session_scope() as s:
            m = s.execute(
                select(ProductModel).where(ProductModel.barcode == barcode)
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def save(self, product: Product) -> Product:
        """حفظ المنتج."""
        with session_scope() as s:
            return await self._save_in_session(product, s)

    async def _save_in_session(self, product: Product, session) -> Product:
        """حفظ المنتج في session موجودة (للـ UnitOfWork)."""
        existing = session.execute(
            select(ProductModel).where(ProductModel.id == str(product.id))
        ).scalar_one_or_none()
        m = self._to_model(product, existing)
        session.add(m)
        session.flush()
        session.refresh(m)
        return self._to_entity(m)

    async def delete(self, product_id: UUID) -> bool:
        with session_scope() as s:
            m = s.execute(
                select(ProductModel).where(ProductModel.id == str(product_id))
            ).scalar_one_or_none()
            if m is None:
                return False
            s.delete(m)
            return True

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Product]:
        with session_scope() as s:
            stmt = (
                select(ProductModel)
                .where(ProductModel.is_active == True)  # noqa: E712
                .order_by(ProductModel.sku)
                .offset(skip)
                .limit(limit)
            )
            models = s.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]

    async def search(self, query: str, limit: int = 10) -> list[Product]:
        with session_scope() as s:
            pattern = f"%{query}%"
            stmt = (
                select(ProductModel)
                .where(
                    or_(
                        ProductModel.name.ilike(pattern),
                        ProductModel.sku.ilike(pattern),
                        ProductModel.barcode.ilike(pattern),
                    )
                )
                .limit(limit)
            )
            models = s.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]


class SqlAlchemyInventoryRepository(IInventoryRepository):
    def _to_entity(self, m: InventoryEntryModel) -> InventoryEntry:
        """ To Entity."""
        return InventoryEntry(
            id=UUID(m.id),
            product_id=UUID(m.product_id),
            quantity_in=Decimal(str(m.quantity_in)),
            quantity_out=Decimal(str(m.quantity_out)),
            reference_type=m.reference_type,
            reference_id=UUID(m.reference_id) if m.reference_id else None,
            unit_cost=Decimal(str(m.unit_cost)),
            balance_after=Decimal(str(m.balance_after)),
            created_at=m.created_at,
            created_by=UUID(m.created_by) if m.created_by else None,  # type: ignore
        )

    async def get_balance(self, product_id: UUID) -> float:
        with session_scope() as s:
            stmt = select(
                func.coalesce(
                    func.sum(InventoryEntryModel.quantity_in)
                    - func.sum(InventoryEntryModel.quantity_out),
                    0,
                )
            ).where(InventoryEntryModel.product_id == str(product_id))
            result = s.execute(stmt).scalar() or 0
            return float(result)

    async def add_entry(self, entry: InventoryEntry) -> InventoryEntry:
        with session_scope() as s:
            m = InventoryEntryModel(
                id=str(entry.id),
                product_id=str(entry.product_id),
                quantity_in=entry.quantity_in,
                quantity_out=entry.quantity_out,
                reference_type=entry.reference_type,
                reference_id=str(entry.reference_id) if entry.reference_id else None,
                unit_cost=entry.unit_cost,
                balance_after=entry.balance_after,
                created_by=str(entry.created_by) if entry.created_by else None,
            )
            s.add(m)
            s.flush()
            s.refresh(m)
            return self._to_entity(m)

    async def list_entries(
        self, product_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[InventoryEntry]:
        with session_scope() as s:
            stmt = (
                select(InventoryEntryModel)
                .where(InventoryEntryModel.product_id == str(product_id))
                .order_by(InventoryEntryModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            models = s.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]

    async def get_low_stock_products(self) -> list[tuple]:
        """المنتجات تحت الحد الأدنى — يُعيد [(product, current_balance), ...]

        Product is returned as ProductModel (ORM) for performance.
        Caller should convert to entity if needed.
        """
        with session_scope() as s:
            # Compute balances per product
            balance_subq = (
                select(
                    InventoryEntryModel.product_id.label("pid"),
                    (
                        func.sum(InventoryEntryModel.quantity_in)
                        - func.sum(InventoryEntryModel.quantity_out)
                    ).label("balance"),
                )
                .group_by(InventoryEntryModel.product_id)
                .subquery()
            )

            stmt = (
                select(ProductModel, func.coalesce(balance_subq.c.balance, 0))
                .outerjoin(balance_subq, ProductModel.id == balance_subq.c.pid)
                .where(
                    and_(
                        ProductModel.is_active == True,  # noqa: E712
                        ProductModel.min_stock_level > 0,
                        func.coalesce(balance_subq.c.balance, 0) < ProductModel.min_stock_level,
                    )
                )
                .order_by(ProductModel.sku)
            )
            results = s.execute(stmt).all()
            # Detach models from session for use outside
            output = []
            for p, b in results:
                s.expunge(p)
                output.append((p, float(b)))
            return output
