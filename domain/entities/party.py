"""
Customer & Supplier Entities - كيانات العملاء والموردين
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from domain.exceptions.exceptions import ValidationException
from domain.value_objects.value_objects import Money


@dataclass
class Party:
    """كيان قاعدي مشترك بين Customer و Supplier.

    نفس الحقول تقريبًا، الاختلاف في طبيعة الرصيد:
    - Customer: مدين لنا (نحن نبيع له)
    - Supplier: دائن علينا (نحن نشتري منه)
    """

    id: UUID = field(default_factory=uuid4)
    code: str = ""  # كود فريد
    name: str = ""
    name_en: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    tax_number: str = ""  # الرقم الضريبي
    opening_balance: Decimal = field(default_factory=lambda: Decimal("0"))
    current_balance: Decimal = field(default_factory=lambda: Decimal("0"))
    credit_limit: Decimal = field(default_factory=lambda: Decimal("0"))  # 0 = لا حد
    notes: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("code is required")
        if not self.name:
            raise ValueError("name is required")
        if self.opening_balance < 0:
            raise ValidationException("opening_balance", "cannot be negative")
        if self.current_balance < 0:
            raise ValidationException("current_balance", "cannot be negative")
        if self.credit_limit < 0:
            raise ValidationException("credit_limit", "cannot be negative")

    def update_balance(self, amount: Decimal) -> None:
        """تحديث الرصيد بمبلغ (موجب = زيادة، سالب = نقص)."""
        new_balance = self.current_balance + amount
        if new_balance < 0:
            raise ValidationException(
                "balance", f"cannot go negative: {self.current_balance} + {amount}"
            )
        self.current_balance = new_balance
        self.updated_at = datetime.now()

    def has_credit_limit(self) -> bool:
        """هل تم تحديد حد ائتماني؟"""
        return self.credit_limit > 0

    def is_within_credit_limit(self, additional_amount: Decimal = 0) -> bool:
        """هل الرصيد (مع المبلغ الإضافي) ضمن حد الائتمان؟"""
        if not self.has_credit_limit():
            return True
        return (self.current_balance + additional_amount) <= self.credit_limit

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "code": self.code,
            "name": self.name,
            "name_en": self.name_en,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "tax_number": self.tax_number,
            "opening_balance": str(self.opening_balance),
            "current_balance": str(self.current_balance),
            "credit_limit": str(self.credit_limit),
            "is_active": self.is_active,
            "notes": self.notes,
        }


@dataclass
class Customer(Party):
    """كيان العميل: يبيع له الشركة، رصيده مدين لنا."""

    # Customer-specific fields
    customer_category: str = "regular"
    payment_terms_days: int = 30  # آجل 30 يومًا افتراضيًا


@dataclass
class Supplier(Party):
    """كيان المورد: تشتري منه الشركة، رصيده دائن علينا."""

    # Supplier-specific fields
    supplier_category: str = "regular"
    payment_terms_days: int = 30
