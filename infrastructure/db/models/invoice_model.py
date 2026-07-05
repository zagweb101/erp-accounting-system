"""SQLAlchemy Invoice & InvoiceItems models."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Numeric, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.session import Base


class InvoiceModel(Base):
    """نموذج الفاتورة (بيع/شراء/مرتجع)."""

    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    invoice_type: Mapped[str] = mapped_column(String(20), nullable=False)  # SALE/PURCHASE/RETURN
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=True)
    supplier_id: Mapped[str] = mapped_column(String(36), ForeignKey("suppliers.id"), nullable=True)
    issue_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    subtotal: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    discount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    journal_entry_id: Mapped[str] = mapped_column(String(36), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    items: Mapped[list["InvoiceItemModel"]] = relationship(
        "InvoiceItemModel",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<InvoiceModel(no={self.invoice_no!r}, type={self.invoice_type}, total={self.total})>"


class InvoiceItemModel(Base):
    """نموذج بند الفاتورة."""

    __tablename__ = "invoice_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(15, 2), default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=15.0)
    discount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    description: Mapped[str] = mapped_column(Text, default="")

    invoice: Mapped["InvoiceModel"] = relationship("InvoiceModel", back_populates="items")

    def __repr__(self) -> str:
        return f"<InvoiceItemModel(qty={self.quantity}, price={self.unit_price})>"
