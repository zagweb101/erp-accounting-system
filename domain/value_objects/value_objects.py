"""
Value Objects - كائنات القيمة

كائنات غير قابلة للتعديل (immutable) تمثل مفاهيم محاسبية صرفة.
لا هوية لها (identity-less): قيمتان متساويتان = نفس الكائن.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from domain.exceptions.exceptions import (
    NegativeAmountException,
    ValidationException,
)


# ============================================================
# Money Value Object
# ============================================================
@dataclass(frozen=True)
class Money:
    """كائن قيمة يمثل مبلغًا ماليًا.

    نستخدم Decimal بدلًا من float لتجنب أخطاء التقريب.
    المبلغ لا يمكن أن يكون سالبًا (السالب يُمثَّل بإشارة معاملة منفصلة).
    """

    amount: Decimal
    currency: str = "SAR"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if self.amount < 0:
            raise NegativeAmountException("money.amount")
        if not self.currency or len(self.currency) != 3:
            raise ValidationException("currency", "must be 3-letter ISO code")

    @classmethod
    def from_float(cls, amount: float, currency: str = "SAR") -> Money:
        return cls(Decimal(str(amount)), currency)

    @classmethod
    def zero(cls, currency: str = "SAR") -> Money:
        return cls(Decimal("0"), currency)

    def add(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: Money) -> Money:
        self._check_currency(other)
        result = self.amount - other.amount
        if result < 0:
            raise NegativeAmountException("subtraction result")
        return Money(result, self.currency)

    def multiply(self, factor: Decimal | int | float) -> Money:
        if factor < 0:
            raise NegativeAmountException("factor")
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def is_zero(self) -> bool:
        return self.amount == 0

    def is_positive(self) -> bool:
        return self.amount > 0

    def to_float(self) -> float:
        return float(self.amount)

    def format(self) -> str:
        """عرض بالمظهر العربي: 1,234.56 ر.س"""
        formatted = f"{self.amount:,.2f}"
        return f"{formatted} {self.currency}"

    def _check_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValidationException(
                "currency",
                f"currency mismatch: {self.currency} vs {other.currency}",
            )

    def __str__(self) -> str:
        return self.format()


# ============================================================
# Quantity Value Object
# ============================================================
@dataclass(frozen=True)
class Quantity:
    """كائن قيمة يمثل كمية منتج."""

    value: Decimal
    unit: str = "piece"

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))
        if self.value < 0:
            raise NegativeAmountException("quantity.value")

    @classmethod
    def from_float(cls, value: float, unit: str = "piece") -> Quantity:
        return cls(Decimal(str(value)), unit)

    def add(self, other: Quantity) -> Quantity:
        self._check_unit(other)
        return Quantity(self.value + other.value, self.unit)

    def subtract(self, other: Quantity) -> Quantity:
        self._check_unit(other)
        result = self.value - other.value
        if result < 0:
            raise NegativeAmountException("quantity subtraction")
        return Quantity(result, self.unit)

    def is_zero(self) -> bool:
        return self.value == 0

    def to_float(self) -> float:
        return float(self.value)

    def _check_unit(self, other: Quantity) -> None:
        if self.unit != other.unit:
            raise ValidationException("unit", f"unit mismatch: {self.unit} vs {other.unit}")

    def __str__(self) -> str:
        return f"{self.value} {self.unit}"


# ============================================================
# Account Code Value Object
# ============================================================
@dataclass(frozen=True)
class AccountCode:
    """كائن قيمة يمثل كود حساب محاسبي.

    الكود هرمي: 1 (أصول) → 11 (متداولة) → 1101 (الصندوق).
    يجب أن يكون أرقامًا فقط، طول 1-10.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValidationException("account_code", "cannot be empty")
        if not self.value.isdigit():
            raise ValidationException("account_code", "must be digits only")
        if not (1 <= len(self.value) <= 10):
            raise ValidationException("account_code", "length must be 1-10 digits")

    @property
    def level(self) -> int:
        """مستوى الحساب في الشجرة (1 = رئيسي، 2 = فرعي، إلخ)."""
        return len(self.value)

    @property
    def parent_code(self) -> AccountCode | None:
        """كود الحساب الأب (إذا وُجد)."""
        if len(self.value) <= 1:
            return None
        return AccountCode(self.value[:-1])

    def is_child_of(self, parent: AccountCode) -> bool:
        """هل هذا الحساب فرع من حساب آخر؟"""
        return self.value.startswith(parent.value) and self.value != parent.value

    def __str__(self) -> str:
        return self.value


# ============================================================
# Account Type Enum
# ============================================================
class AccountType(str, Enum):
    """أنواع الحسابات الخمسة في القيد المزدوج."""

    ASSET = "ASSET"           # أصول (طبيعة مدين)
    LIABILITY = "LIABILITY"   # خصوم (طبيعة دائن)
    EQUITY = "EQUITY"         # حقوق ملكية (طبيعة دائن)
    REVENUE = "REVENUE"       # إيرادات (طبيعة دائن)
    EXPENSE = "EXPENSE"       # مصروفات (طبيعة مدين)

    @property
    def normal_balance(self) -> str:
        """الطبيعة الطبيعية للرصيد: DEBIT أو CREDIT."""
        return "DEBIT" if self in (AccountType.ASSET, AccountType.EXPENSE) else "CREDIT"

    @property
    def arabic_name(self) -> str:
        names = {
            AccountType.ASSET: "أصول",
            AccountType.LIABILITY: "خصوم",
            AccountType.EQUITY: "حقوق ملكية",
            AccountType.REVENUE: "إيرادات",
            AccountType.EXPENSE: "مصروفات",
        }
        return names[self]


# ============================================================
# Invoice Type Enum
# ============================================================
class InvoiceType(str, Enum):
    SALE = "SALE"               # فاتورة بيع
    PURCHASE = "PURCHASE"       # فاتورة شراء
    SALE_RETURN = "SALE_RETURN"  # مرتجع بيع
    PURCHASE_RETURN = "PURCHASE_RETURN"  # مرتجع شراء


class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"             # مسودة
    POSTED = "POSTED"           # مُرحَّلة (ولّدت القيد)
    PAID_PARTIAL = "PAID_PARTIAL"  # مدفوعة جزئيًا
    PAID_FULL = "PAID_FULL"     # مدفوعة كاملة
    CANCELLED = "CANCELLED"     # ملغاة


# ============================================================
# User Role Enum
# ============================================================
class UserRole(str, Enum):
    ACCOUNTANT = "ACCOUNTANT"     # محاسب
    FINANCIAL_MANAGER = "FINANCIAL_MANAGER"  # مدير مالي
    COMPANY_OWNER = "COMPANY_OWNER"  # صاحب شركة
    INVENTORY_CLERK = "INVENTORY_CLERK"  # موظف مخزون
    ADMIN = "ADMIN"              # مدير النظام


# ============================================================
# Permissions
# ============================================================
class Permission(str, Enum):
    """صلاحيات دقيقة على مستوى العمليات."""

    # Users
    USER_VIEW = "user.view"
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"

    # Customers
    CUSTOMER_VIEW = "customer.view"
    CUSTOMER_CREATE = "customer.create"
    CUSTOMER_UPDATE = "customer.update"
    CUSTOMER_DELETE = "customer.delete"

    # Suppliers
    SUPPLIER_VIEW = "supplier.view"
    SUPPLIER_CREATE = "supplier.create"
    SUPPLIER_UPDATE = "supplier.update"
    SUPPLIER_DELETE = "supplier.delete"

    # Products
    PRODUCT_VIEW = "product.view"
    PRODUCT_CREATE = "product.create"
    PRODUCT_UPDATE = "product.update"
    PRODUCT_DELETE = "product.delete"

    # Invoices
    INVOICE_VIEW = "invoice.view"
    INVOICE_CREATE = "invoice.create"
    INVOICE_UPDATE = "invoice.update"
    INVOICE_DELETE = "invoice.delete"
    INVOICE_POST = "invoice.post"  # ترحيل (توليد القيد)

    # Journal
    JOURNAL_VIEW = "journal.view"
    JOURNAL_CREATE = "journal.create"
    JOURNAL_POST = "journal.post"

    # Reports
    REPORT_VIEW = "report.view"
    REPORT_EXPORT = "report.export"

    # Settings
    SETTINGS_VIEW = "settings.view"
    SETTINGS_UPDATE = "settings.update"

    # Backup
    BACKUP_CREATE = "backup.create"
    BACKUP_RESTORE = "backup.restore"


# Role → Permissions mapping (RBAC)
ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ACCOUNTANT: frozenset({
        Permission.CUSTOMER_VIEW, Permission.CUSTOMER_CREATE, Permission.CUSTOMER_UPDATE,
        Permission.SUPPLIER_VIEW, Permission.SUPPLIER_CREATE, Permission.SUPPLIER_UPDATE,
        Permission.PRODUCT_VIEW, Permission.PRODUCT_CREATE, Permission.PRODUCT_UPDATE,
        Permission.INVOICE_VIEW, Permission.INVOICE_CREATE, Permission.INVOICE_UPDATE, Permission.INVOICE_POST,
        Permission.JOURNAL_VIEW, Permission.JOURNAL_CREATE, Permission.JOURNAL_POST,
        Permission.REPORT_VIEW, Permission.REPORT_EXPORT,
        Permission.SETTINGS_VIEW,
    }),
    UserRole.FINANCIAL_MANAGER: frozenset({
        # كل صلاحيات المحاسب +
        Permission.CUSTOMER_VIEW, Permission.CUSTOMER_CREATE, Permission.CUSTOMER_UPDATE, Permission.CUSTOMER_DELETE,
        Permission.SUPPLIER_VIEW, Permission.SUPPLIER_CREATE, Permission.SUPPLIER_UPDATE, Permission.SUPPLIER_DELETE,
        Permission.PRODUCT_VIEW, Permission.PRODUCT_CREATE, Permission.PRODUCT_UPDATE, Permission.PRODUCT_DELETE,
        Permission.INVOICE_VIEW, Permission.INVOICE_CREATE, Permission.INVOICE_UPDATE, Permission.INVOICE_DELETE, Permission.INVOICE_POST,
        Permission.JOURNAL_VIEW, Permission.JOURNAL_CREATE, Permission.JOURNAL_POST,
        Permission.REPORT_VIEW, Permission.REPORT_EXPORT,
        Permission.SETTINGS_VIEW, Permission.SETTINGS_UPDATE,
        Permission.USER_VIEW, Permission.USER_CREATE, Permission.USER_UPDATE,
        Permission.BACKUP_CREATE,
    }),
    UserRole.COMPANY_OWNER: frozenset({
        Permission.CUSTOMER_VIEW, Permission.SUPPLIER_VIEW, Permission.PRODUCT_VIEW,
        Permission.INVOICE_VIEW, Permission.JOURNAL_VIEW,
        Permission.REPORT_VIEW, Permission.REPORT_EXPORT,
        Permission.SETTINGS_VIEW, Permission.SETTINGS_UPDATE,
        Permission.BACKUP_CREATE, Permission.BACKUP_RESTORE,
    }),
    UserRole.INVENTORY_CLERK: frozenset({
        Permission.PRODUCT_VIEW, Permission.PRODUCT_CREATE, Permission.PRODUCT_UPDATE,
        # Inventory operations only (no financial)
    }),
    UserRole.ADMIN: frozenset(Permission),  # كل الصلاحيات
}
