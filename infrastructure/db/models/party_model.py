"""SQLAlchemy Customer & Supplier models."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Numeric, Text, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.session import Base


class CustomerModel(Base):
    """نموذج العميل."""

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    tax_number: Mapped[str] = mapped_column(String(50), default="")
    opening_balance: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    current_balance: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    credit_limit: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    customer_category: Mapped[str] = mapped_column(String(50), default="regular")
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)
    notes: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<CustomerModel(code={self.code!r}, name={self.name!r})>"


class SupplierModel(Base):
    """نموذج المورد."""

    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    tax_number: Mapped[str] = mapped_column(String(50), default="")
    opening_balance: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    current_balance: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    credit_limit: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    supplier_category: Mapped[str] = mapped_column(String(50), default="regular")
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)
    notes: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<SupplierModel(code={self.code!r}, name={self.name!r})>"
