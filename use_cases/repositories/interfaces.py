"""
Repository Interfaces (Ports) - واجهات المستودعات

هذه واجهات (abstract) تُعرّف في طبقة Use Cases، لكن تُنفَّذ في طبقة Adapters.
هذا الفصل هو جوهر Clean Architecture: منطق الأعمال لا يعرف كيف تُخزَّن البيانات.
"""
from __future__ import annotations

import abc
from typing import Optional
from uuid import UUID

from domain.entities.account import Account
from domain.entities.invoice import Invoice, InvoiceType
from domain.entities.journal import JournalEntry
from domain.entities.party import Customer, Supplier
from domain.entities.product import InventoryEntry, Product
from domain.entities.user import User


# ============================================================
# User Repository
# ============================================================
class IUserRepository(abc.ABC):
    """واجهة مستودع المستخدمين."""

    @abc.abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        ...

    @abc.abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        ...

    @abc.abstractmethod
    async def save(self, user: User) -> User:
        ...

    @abc.abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        ...

    @abc.abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        ...


# ============================================================
# Account Repository
# ============================================================
class IAccountRepository(abc.ABC):
    """واجهة مستودع الحسابات المحاسبية."""

    @abc.abstractmethod
    async def get_by_id(self, account_id: UUID) -> Optional[Account]:
        ...

    @abc.abstractmethod
    async def get_by_code(self, code: str) -> Optional[Account]:
        ...

    @abc.abstractmethod
    async def save(self, account: Account) -> Account:
        ...

    @abc.abstractmethod
    async def list_by_type(self, account_type: str) -> list[Account]:
        ...

    @abc.abstractmethod
    async def list_children(self, parent_id: UUID) -> list[Account]:
        ...

    @abc.abstractmethod
    async def get_account_balance(self, account_id: UUID) -> float:
        """الرصيد الحالي للحساب (محسوب من القيود المرحَّلة)."""
        ...


# ============================================================
# Journal Entry Repository
# ============================================================
class IJournalEntryRepository(abc.ABC):
    """واجهة مستودع القيود المحاسبية."""

    @abc.abstractmethod
    async def get_by_id(self, entry_id: UUID) -> Optional[JournalEntry]:
        ...

    @abc.abstractmethod
    async def get_by_no(self, entry_no: str) -> Optional[JournalEntry]:
        ...

    @abc.abstractmethod
    async def save(self, entry: JournalEntry) -> JournalEntry:
        ...

    @abc.abstractmethod
    async def list_by_date_range(
        self, start_date, end_date, skip: int = 0, limit: int = 100
    ) -> list[JournalEntry]:
        ...

    @abc.abstractmethod
    async def list_by_account(
        self, account_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[JournalEntry]:
        ...

    @abc.abstractmethod
    async def next_entry_no(self) -> str:
        """توليد رقم قيد تسلسلي."""
        ...


# ============================================================
# Customer Repository
# ============================================================
class ICustomerRepository(abc.ABC):
    """واجهة مستودع العملاء."""

    @abc.abstractmethod
    async def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        ...

    @abc.abstractmethod
    async def get_by_code(self, code: str) -> Optional[Customer]:
        ...

    @abc.abstractmethod
    async def save(self, customer: Customer) -> Customer:
        ...

    @abc.abstractmethod
    async def delete(self, customer_id: UUID) -> bool:
        ...

    @abc.abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Customer]:
        ...

    @abc.abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[Customer]:
        ...


# ============================================================
# Supplier Repository
# ============================================================
class ISupplierRepository(abc.ABC):
    """واجهة مستودع الموردين."""

    @abc.abstractmethod
    async def get_by_id(self, supplier_id: UUID) -> Optional[Supplier]:
        ...

    @abc.abstractmethod
    async def get_by_code(self, code: str) -> Optional[Supplier]:
        ...

    @abc.abstractmethod
    async def save(self, supplier: Supplier) -> Supplier:
        ...

    @abc.abstractmethod
    async def delete(self, supplier_id: UUID) -> bool:
        ...

    @abc.abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Supplier]:
        ...


# ============================================================
# Product Repository
# ============================================================
class IProductRepository(abc.ABC):
    """واجهة مستودع المنتجات."""

    @abc.abstractmethod
    async def get_by_id(self, product_id: UUID) -> Optional[Product]:
        ...

    @abc.abstractmethod
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        ...

    @abc.abstractmethod
    async def get_by_barcode(self, barcode: str) -> Optional[Product]:
        ...

    @abc.abstractmethod
    async def save(self, product: Product) -> Product:
        ...

    @abc.abstractmethod
    async def delete(self, product_id: UUID) -> bool:
        ...

    @abc.abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Product]:
        ...

    @abc.abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[Product]:
        ...


# ============================================================
# Inventory Repository
# ============================================================
class IInventoryRepository(abc.ABC):
    """واجهة مستودع المخزون."""

    @abc.abstractmethod
    async def get_balance(self, product_id: UUID) -> float:
        """الرصيد الحالي لمنتج."""
        ...

    @abc.abstractmethod
    async def add_entry(self, entry: InventoryEntry) -> InventoryEntry:
        """تسجيل حركة مخزون."""
        ...

    @abc.abstractmethod
    async def list_entries(
        self, product_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[InventoryEntry]:
        ...

    @abc.abstractmethod
    async def get_low_stock_products(self) -> list[tuple[Product, float]]:
        """المنتجات تحت الحد الأدنى."""
        ...


# ============================================================
# Invoice Repository
# ============================================================
class IInvoiceRepository(abc.ABC):
    """واجهة مستودع الفواتير."""

    @abc.abstractmethod
    async def get_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        ...

    @abc.abstractmethod
    async def get_by_no(self, invoice_no: str) -> Optional[Invoice]:
        ...

    @abc.abstractmethod
    async def save(self, invoice: Invoice) -> Invoice:
        ...

    @abc.abstractmethod
    async def list_all(
        self,
        invoice_type: Optional[InvoiceType] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Invoice]:
        ...

    @abc.abstractmethod
    async def list_by_customer(
        self, customer_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Invoice]:
        ...

    @abc.abstractmethod
    async def list_by_supplier(
        self, supplier_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Invoice]:
        ...

    @abc.abstractmethod
    async def next_invoice_no(self, invoice_type: InvoiceType) -> str:
        """توليد رقم فاتورة تسلسلي حسب النوع."""
        ...
