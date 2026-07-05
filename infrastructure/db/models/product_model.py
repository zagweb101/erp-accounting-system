"""SQLAlchemy Product & Inventory models."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Numeric, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.session import Base


class ProductModel(Base):
    """نموذج المنتج."""

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    barcode: Mapped[str] = mapped_column(String(100), default="", index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(100), default="", index=True)
    unit: Mapped[str] = mapped_column(String(50), default="piece")
    cost_price: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    sale_price: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=15.0)
    min_stock_level: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<ProductModel(sku={self.sku!r}, name={self.name!r})>"


class InventoryEntryModel(Base):
    """نموذج حركة مخزون."""

    __tablename__ = "inventory_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    quantity_in: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    quantity_out: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    reference_type: Mapped[str] = mapped_column(String(20), default="")
    reference_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    unit_cost: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    balance_after: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=True)

    def __repr__(self) -> str:
        side = "IN" if self.quantity_in > 0 else "OUT"
        qty = self.quantity_in if self.quantity_in > 0 else self.quantity_out
        return f"<InventoryEntryModel({side}={qty}, product={self.product_id})>"
