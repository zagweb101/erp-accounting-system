"""
Invoice Entity - كيان الفاتورة (بيع/شراء/مرتجع)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from domain.value_objects.value_objects import InvoiceStatus, InvoiceType


@dataclass
class InvoiceItem:
    """بند الفاتورة."""

    id: UUID = field(default_factory=uuid4)
    invoice_id: UUID = None  # type: ignore
    product_id: UUID = None  # type: ignore
    quantity: Decimal = field(default_factory=lambda: Decimal("1"))
    unit_price: Decimal = field(default_factory=lambda: Decimal("0"))
    tax_rate: Decimal = field(default_factory=lambda: Decimal("15"))
    discount: Decimal = field(default_factory=lambda: Decimal("0"))
    line_total: Decimal = field(default_factory=lambda: Decimal("0"))
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.product_id is None:
            raise ValueError("product_id is required")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.unit_price < 0:
            raise ValueError("unit_price cannot be negative")
        if self.discount < 0:
            raise ValueError("discount cannot be negative")

    def line_subtotal(self) -> Decimal:
        """قبل الضريبة والخصم."""
        return self.unit_price * self.quantity - self.discount

    def line_tax(self) -> Decimal:
        return self.line_subtotal() * self.tax_rate / Decimal("100")


@dataclass
class Invoice:
    """كيان الفاتورة."""

    id: UUID = field(default_factory=uuid4)
    invoice_no: str = ""
    invoice_type: InvoiceType = InvoiceType.SALE
    customer_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    issue_date: datetime = field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    subtotal: Decimal = field(default_factory=lambda: Decimal("0"))
    tax_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    discount: Decimal = field(default_factory=lambda: Decimal("0"))
    total: Decimal = field(default_factory=lambda: Decimal("0"))
    status: InvoiceStatus = InvoiceStatus.DRAFT
    notes: str = ""
    journal_entry_id: Optional[UUID] = None
    created_by: UUID = None  # type: ignore
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    items: list[InvoiceItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.invoice_no:
            raise ValueError("invoice_no is required")
        if self.created_by is None:
            raise ValueError("created_by is required")

    @property
    def is_sale(self) -> bool:
        return self.invoice_type == InvoiceType.SALE

    @property
    def is_purchase(self) -> bool:
        return self.invoice_type == InvoiceType.PURCHASE

    @property
    def is_return(self) -> bool:
        return self.invoice_type in (InvoiceType.SALE_RETURN, InvoiceType.PURCHASE_RETURN)

    def is_paid(self) -> bool:
        return self.status in (InvoiceStatus.PAID_FULL,)

    def is_posted(self) -> bool:
        return self.status in (
            InvoiceStatus.POSTED,
            InvoiceStatus.PAID_PARTIAL,
            InvoiceStatus.PAID_FULL,
        )

    def is_cancelled(self) -> bool:
        return self.status == InvoiceStatus.CANCELLED

    def item_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "invoice_no": self.invoice_no,
            "invoice_type": self.invoice_type.value,
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "supplier_id": str(self.supplier_id) if self.supplier_id else None,
            "issue_date": self.issue_date.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "subtotal": str(self.subtotal),
            "tax_amount": str(self.tax_amount),
            "discount": str(self.discount),
            "total": str(self.total),
            "status": self.status.value,
            "journal_entry_id": str(self.journal_entry_id) if self.journal_entry_id else None,
            "items": [
                {
                    "product_id": str(it.product_id),
                    "quantity": str(it.quantity),
                    "unit_price": str(it.unit_price),
                    "tax_rate": str(it.tax_rate),
                    "discount": str(it.discount),
                    "line_total": str(it.line_total),
                }
                for it in self.items
            ],
        }
