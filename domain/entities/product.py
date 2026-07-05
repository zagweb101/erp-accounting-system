"""
Product & Inventory Entities - كيانات المنتجات والمخزون
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from domain.exceptions.exceptions import (
    InsufficientStockException,
    ValidationException,
)
from domain.value_objects.value_objects import Money, Quantity


@dataclass
class Product:
    """كيان المنتج."""

    id: UUID = field(default_factory=uuid4)
    sku: str = ""  # كود المنتج الفريد
    barcode: str = ""
    name: str = ""
    name_en: str = ""
    description: str = ""
    category: str = ""
    unit: str = "piece"  # الوحدة: piece, kg, liter, box, إلخ
    cost_price: Decimal = field(default_factory=lambda: Decimal("0"))
    sale_price: Decimal = field(default_factory=lambda: Decimal("0"))
    tax_rate: Decimal = field(default_factory=lambda: Decimal("15"))  # 15% VAT السعودية
    min_stock_level: Decimal = field(default_factory=lambda: Decimal("0"))
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.sku:
            raise ValueError("sku is required")
        if not self.name:
            raise ValueError("name is required")
        if self.cost_price < 0:
            raise ValidationException("cost_price", "cannot be negative")
        if self.sale_price < 0:
            raise ValidationException("sale_price", "cannot be negative")
        if not (0 <= self.tax_rate <= 100):
            raise ValidationException("tax_rate", "must be between 0 and 100")

    def profit_margin(self) -> Decimal:
        """هامش الربح (نسبة)."""
        if self.cost_price == 0:
            return Decimal("0")
        return ((self.sale_price - self.cost_price) / self.cost_price) * 100

    def tax_amount(self, quantity: Decimal = Decimal("1")) -> Decimal:
        """ضريبة الوحدة الواحدة × الكمية."""
        return (self.sale_price * quantity * self.tax_rate / 100)

    def line_total(self, quantity: Decimal = Decimal("1")) -> Decimal:
        """إجمالي البند (شامل الضريبة)."""
        return self.sale_price * quantity + self.tax_amount(quantity)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "sku": self.sku,
            "barcode": self.barcode,
            "name": self.name,
            "name_en": self.name_en,
            "description": self.description,
            "category": self.category,
            "unit": self.unit,
            "cost_price": str(self.cost_price),
            "sale_price": str(self.sale_price),
            "tax_rate": str(self.tax_rate),
            "min_stock_level": str(self.min_stock_level),
            "is_active": self.is_active,
            "profit_margin": str(self.profit_margin()),
        }


@dataclass
class InventoryEntry:
    """حركة مخزون واحدة (وارد أو صادر)."""

    id: UUID = field(default_factory=uuid4)
    product_id: UUID = None  # type: ignore
    quantity_in: Decimal = field(default_factory=lambda: Decimal("0"))
    quantity_out: Decimal = field(default_factory=lambda: Decimal("0"))
    reference_type: str = ""  # invoice, return, adjustment, opening
    reference_id: Optional[UUID] = None
    unit_cost: Decimal = field(default_factory=lambda: Decimal("0"))  # التكلفة وقت الحركة
    balance_after: Decimal = field(default_factory=lambda: Decimal("0"))  # الرصيد بعد الحركة
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: UUID = None  # type: ignore

    def __post_init__(self) -> None:
        if self.product_id is None:
            raise ValueError("product_id is required")
        if self.quantity_in < 0 or self.quantity_out < 0:
            raise ValidationException("quantity", "cannot be negative")
        if self.quantity_in > 0 and self.quantity_out > 0:
            raise ValueError("cannot have both quantity_in and quantity_out in same entry")

    @property
    def is_in(self) -> bool:
        return self.quantity_in > 0

    @property
    def is_out(self) -> bool:
        return self.quantity_out > 0

    @property
    def net_quantity(self) -> Decimal:
        """الكمية الصافية (موجب = وارد، سالب = صادر)."""
        return self.quantity_in - self.quantity_out
