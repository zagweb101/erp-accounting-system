"""
Journal Entry Entities - كيانات القيود المحاسبية

قلب القيد المزدوج: JournalEntry (قيد) + JournalLine (بند قيد).
القيد متوازن دائمًا: مجموع المدين = مجموع الدائن.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from domain.exceptions.exceptions import (
    JournalEntryAlreadyPostedException,
    UnbalancedJournalEntryException,
)
from domain.value_objects.value_objects import Money


class JournalEntryStatus(str, Enum):
    DRAFT = "DRAFT"       # مسودة (قابلة للتعديل)
    POSTED = "POSTED"     # مُرحَّلة (ولّدت أثرها على الأرصدة، غير قابلة للتعديل)
    REVERSED = "REVERSED"  # مقلوبة (بقيد عكسي)


class JournalEntryReferenceType(str, Enum):
    """نوع المستند المرجعي للقيد."""

    INVOICE = "INVOICE"           # فاتورة
    RETURN = "RETURN"             # مرتجع
    EXPENSE = "EXPENSE"           # مصروف
    PAYMENT = "PAYMENT"           # دفعة
    ADJUSTMENT = "ADJUSTMENT"     # قيد تسوية
    OPENING = "OPENING"           # قيد افتتاحي
    CLOSING = "CLOSING"           # قيد إقفال
    MANUAL = "MANUAL"             # قيد يدوي


@dataclass
class JournalLine:
    """بند قيد: سطر واحد من القيد (مدين أو دائن)."""

    id: UUID = field(default_factory=uuid4)
    entry_id: UUID = None  # type: ignore
    account_id: UUID = None  # type: ignore
    debit: Decimal = field(default_factory=lambda: Decimal("0"))
    credit: Decimal = field(default_factory=lambda: Decimal("0"))
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.account_id is None:
            raise ValueError("account_id is required")
        # إما مدين أو دائن، لا الاثنان معًا ولا لا شيء (إلا إذا كان صفرًا كلاهما)
        if self.debit > 0 and self.credit > 0:
            raise ValueError("journal line cannot have both debit and credit")
        if self.debit < 0 or self.credit < 0:
            raise ValueError("debit and credit cannot be negative")

    @property
    def amount(self) -> Decimal:
        """المبلغ (سواء مدين أو دائن)."""
        return self.debit if self.debit > 0 else self.credit

    @property
    def is_debit(self) -> bool:
        return self.debit > 0

    @property
    def is_credit(self) -> bool:
        return self.credit > 0

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "entry_id": str(self.entry_id) if self.entry_id else None,
            "account_id": str(self.account_id),
            "debit": str(self.debit),
            "credit": str(self.credit),
            "description": self.description,
        }


@dataclass
class JournalEntry:
    """قيد محاسبي: مجموعة بنود متوازنة (مدين = دائن).

    القاعدة الذهبية: لا يمكن حفظ قيد غير متوازن.
    """

    id: UUID = field(default_factory=uuid4)
    entry_no: str = ""  # رقم القيد التسلسلي
    date: datetime = field(default_factory=datetime.utcnow)
    reference_type: JournalEntryReferenceType = JournalEntryReferenceType.MANUAL
    reference_id: Optional[UUID] = None
    description: str = ""
    status: JournalEntryStatus = JournalEntryStatus.DRAFT
    created_by: UUID = None  # type: ignore
    posted_by: Optional[UUID] = None
    posted_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    lines: list[JournalLine] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.entry_no:
            raise ValueError("entry_no is required")
        if self.created_by is None:
            raise ValueError("created_by is required")

    # ============================================================
    # Lines management
    # ============================================================
    def add_line(
        self,
        account_id: UUID,
        debit: Decimal | float | int = 0,
        credit: Decimal | float | int = 0,
        description: str = "",
    ) -> JournalLine:
        """إضافة بند للقيد."""
        if self.status == JournalEntryStatus.POSTED:
            raise JournalEntryAlreadyPostedException(self.entry_no)

        line = JournalLine(
            entry_id=self.id,
            account_id=account_id,
            debit=Decimal(str(debit)),
            credit=Decimal(str(credit)),
            description=description,
        )
        self.lines.append(line)
        self.updated_at = datetime.now()
        return line

    def remove_line(self, line_id: UUID) -> None:
        """حذف بند من القيد."""
        if self.status == JournalEntryStatus.POSTED:
            raise JournalEntryAlreadyPostedException(self.entry_no)
        self.lines = [l for l in self.lines if l.id != line_id]
        self.updated_at = datetime.now()

    # ============================================================
    # Balance verification (Double-Entry Rule)
    # ============================================================
    def total_debit(self) -> Decimal:
        """مجموع المدين."""
        return sum((l.debit for l in self.lines), Decimal("0"))

    def total_credit(self) -> Decimal:
        """مجموع الدائن."""
        return sum((l.credit for l in self.lines), Decimal("0"))

    def is_balanced(self) -> bool:
        """هل القيد متوازن؟ (مدين = دائن)."""
        return self.total_debit() == self.total_credit()

    def difference(self) -> Decimal:
        """الفرق بين المدين والدائن (يجب أن يكون صفرًا)."""
        return self.total_debit() - self.total_credit()

    def assert_balanced(self) -> None:
        """رمي استثناء إذا كان القيد غير متوازن."""
        if not self.is_balanced():
            raise UnbalancedJournalEntryException(
                float(self.total_debit()),
                float(self.total_credit()),
            )

    def has_lines(self) -> bool:
        """هل يحتوي القيد على بنود؟"""
        return len(self.lines) > 0

    def line_count(self) -> int:
        return len(self.lines)

    # ============================================================
    # Status transitions
    # ============================================================
    def post(self, posted_by: UUID) -> None:
        """ترحيل القيد: قفله وتوليد أثره على الأرصدة."""
        if self.status == JournalEntryStatus.POSTED:
            raise JournalEntryAlreadyPostedException(self.entry_no)
        if not self.has_lines():
            raise ValueError("cannot post empty journal entry")
        self.assert_balanced()
        self.status = JournalEntryStatus.POSTED
        self.posted_by = posted_by
        self.posted_at = datetime.now()
        self.updated_at = datetime.now()

    def reverse(self, reversed_by: UUID) -> JournalEntry:
        """إنشاء قيد عكسي (لإلغاء قيد مرحّل).

        القيد العكسي يبدل المدين والدائن في كل بند.
        """
        if self.status != JournalEntryStatus.POSTED:
            raise ValueError("only posted entries can be reversed")

        reversed_entry = JournalEntry(
            entry_no=f"REV-{self.entry_no}",
            date=datetime.now(),
            reference_type=JournalEntryReferenceType.ADJUSTMENT,
            reference_id=self.id,
            description=f"قيد عكسي لـ {self.entry_no}: {self.description}",
            status=JournalEntryStatus.DRAFT,
            created_by=reversed_by,
        )
        for line in self.lines:
            reversed_entry.add_line(
                account_id=line.account_id,
                debit=line.credit,  # عكس
                credit=line.debit,  # عكس
                description=f"عكسي: {line.description}",
            )
        reversed_entry.post(reversed_by)
        self.status = JournalEntryStatus.REVERSED
        self.updated_at = datetime.now()
        return reversed_entry

    # ============================================================
    # Validation before save
    # ============================================================
    def validate(self) -> list[str]:
        """إرجاع قائمة بأخطاء التحقق (قائمة فارغة = صحيح)."""
        errors: list[str] = []
        if not self.entry_no:
            errors.append("entry_no is required")
        if not self.has_lines():
            errors.append("entry must have at least one line")
        if self.has_lines() and not self.is_balanced():
            errors.append(
                f"entry is not balanced: debit={self.total_debit()}, "
                f"credit={self.total_credit()}, diff={self.difference()}"
            )
        # كل بند يجب أن يكون له account_id
        for i, line in enumerate(self.lines):
            if line.account_id is None:
                errors.append(f"line {i + 1}: account_id is required")
        return errors

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "entry_no": self.entry_no,
            "date": self.date.isoformat(),
            "reference_type": self.reference_type.value,
            "reference_id": str(self.reference_id) if self.reference_id else None,
            "description": self.description,
            "status": self.status.value,
            "created_by": str(self.created_by),
            "posted_by": str(self.posted_by) if self.posted_by else None,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "total_debit": str(self.total_debit()),
            "total_credit": str(self.total_credit()),
            "is_balanced": self.is_balanced(),
            "lines": [l.to_dict() for l in self.lines],
        }
