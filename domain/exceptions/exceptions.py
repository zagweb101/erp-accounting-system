"""
Domain Exceptions - استثناءات طبقة المجال

هذه الاستثناءات مستقلة عن أي مكتبة خارجية، تمثل أخطاء منطق الأعمال.
"""
from __future__ import annotations


class DomainException(Exception):
    """Base class for all domain exceptions."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ============================================================
# User / Auth exceptions
# ============================================================
class UserNotFoundException(DomainException):
    def __init__(self, identifier: str) -> None:
        super().__init__(
            f"المستخدم غير موجود: {identifier}",
            code="USER_NOT_FOUND",
        )


class InvalidCredentialsException(DomainException):
    def __init__(self) -> None:
        super().__init__("اسم المستخدم أو كلمة المرور غير صحيحة", code="INVALID_CREDENTIALS")


class AccountLockedException(DomainException):
    def __init__(self, unlock_at: str | None = None) -> None:
        msg = "تم قفل الحساب بسبب محاولات فاشلة متعددة"
        if unlock_at:
            msg += f". يُفتح في: {unlock_at}"
        super().__init__(msg, code="ACCOUNT_LOCKED")


class PermissionDeniedException(DomainException):
    def __init__(self, required_permission: str) -> None:
        super().__init__(
            f"ليس لديك صلاحية: {required_permission}",
            code="PERMISSION_DENIED",
        )


class UsernameAlreadyExistsException(DomainException):
    def __init__(self, username: str) -> None:
        super().__init__(f"اسم المستخدم موجود بالفعل: {username}", code="USERNAME_EXISTS")


# ============================================================
# Journal / Accounting exceptions
# ============================================================
class UnbalancedJournalEntryException(DomainException):
    """القيد غير متوازن: مجموع المدين ≠ مجموع الدائن."""

    def __init__(self, total_debit: float, total_credit: float) -> None:
        diff = abs(total_debit - total_credit)
        super().__init__(
            f"القيد غير متوازن. المدين: {total_debit:.2f}، الدائن: {total_credit:.2f}، "
            f"الفرق: {diff:.2f}",
            code="UNBALANCED_ENTRY",
        )


class JournalEntryAlreadyPostedException(DomainException):
    def __init__(self, entry_no: str) -> None:
        super().__init__(
            f"لا يمكن تعديل قيد مرحّل: {entry_no}",
            code="ENTRY_ALREADY_POSTED",
        )


class AccountNotFoundException(DomainException):
    def __init__(self, account_code: str) -> None:
        super().__init__(f"الحساب غير موجود: {account_code}", code="ACCOUNT_NOT_FOUND")


class AccountTypeException(DomainException):
    def __init__(self, account_type: str) -> None:
        super().__init__(
            f"نوع حساب غير صالح: {account_type}. يجب أن يكون أحد: "
            "ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE",
            code="INVALID_ACCOUNT_TYPE",
        )


# ============================================================
# Invoice exceptions
# ============================================================
class InvoiceNotFoundException(DomainException):
    def __init__(self, invoice_no: str) -> None:
        super().__init__(f"الفاتورة غير موجودة: {invoice_no}", code="INVOICE_NOT_FOUND")


class InvoiceAlreadyPaidException(DomainException):
    def __init__(self, invoice_no: str) -> None:
        super().__init__(f"الفاتورة مدفوعة بالكامل: {invoice_no}", code="INVOICE_PAID")


class InsufficientStockException(DomainException):
    def __init__(self, product_name: str, requested: float, available: float) -> None:
        super().__init__(
            f"المخزون غير كافٍ للمنتج: {product_name}. المطلوب: {requested}, المتاح: {available}",
            code="INSUFFICIENT_STOCK",
        )


# ============================================================
# Customer / Supplier exceptions
# ============================================================
class CustomerNotFoundException(DomainException):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"العميل غير موجود: {identifier}", code="CUSTOMER_NOT_FOUND")


class ProductNotFoundException(DomainException):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"المنتج غير موجود: {identifier}", code="PRODUCT_NOT_FOUND")


class SupplierNotFoundException(DomainException):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"المورد غير موجود: {identifier}", code="SUPPLIER_NOT_FOUND")


class CreditLimitExceededException(DomainException):
    def __init__(self, customer_name: str, limit: float, current: float) -> None:
        super().__init__(
            f"تجاوز حد الائتمان للعميل: {customer_name}. الحد: {limit:.2f}, الحالي: {current:.2f}",
            code="CREDIT_LIMIT_EXCEEDED",
        )


# ============================================================
# Validation exceptions
# ============================================================
class ValidationException(DomainException):
    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"حقل غير صالح ({field}): {reason}", code="VALIDATION_ERROR")


class NegativeAmountException(DomainException):
    def __init__(self, field: str = "amount") -> None:
        super().__init__(f"لا يمكن أن يكون {field} سالبًا", code="NEGATIVE_AMOUNT")
