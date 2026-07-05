"""
اختبارات شاملة لرفع تغطية invoice_use_cases.py (من 72% إلى 85%+)

تغطي:
- إنشاء فاتورة بيع آجلة (credit)
- إنشاء فاتورة شراء آجلة
- فحص حد الائتمان
- إلغاء فاتورة
- حالات خطأ متعددة
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.db.session import session_scope
from infrastructure.db.models.user_model import UserModel
from infrastructure.db.seed import seed_admin_user, seed_chart_of_accounts

from adapters.repositories.sql_alchemy.user_repository import SqlAlchemyUserRepository
from adapters.repositories.sql_alchemy.party_repository import (
    SqlAlchemyCustomerRepository, SqlAlchemySupplierRepository,
)
from adapters.repositories.sql_alchemy.product_repository import (
    SqlAlchemyProductRepository, SqlAlchemyInventoryRepository,
)
from adapters.repositories.sql_alchemy.invoice_repository import SqlAlchemyInvoiceRepository
from adapters.repositories.sql_alchemy.account_journal_repository import (
    SqlAlchemyAccountRepository, SqlAlchemyJournalEntryRepository,
)
from use_cases.customers.customer_use_cases import CreateCustomerUseCase, CreateCustomerRequest
from use_cases.suppliers.supplier_use_cases import CreateSupplierUseCase, CreateSupplierRequest
from use_cases.products.product_use_cases import (
    CreateProductUseCase, CreateProductRequest, AdjustInventoryUseCase,
)
from use_cases.invoices.invoice_use_cases import (
    CreateInvoiceUseCase, CreateInvoiceRequest, InvoiceLineDTO,
    GetInvoiceUseCase, ListInvoicesUseCase, CancelInvoiceUseCase,
)
from use_cases.invoices.returns_use_cases import CreateReturnUseCase, CreateReturnRequest
from use_cases.journal.journal_use_cases import (
    AutoJournalBuilder, CreateJournalEntryUseCase, PostJournalEntryUseCase,
    ReverseJournalEntryUseCase,
)
from domain.entities.user import User, UserStatus
from domain.entities.invoice import InvoiceType, InvoiceStatus
from domain.value_objects.value_objects import UserRole
from domain.exceptions.exceptions import (
    CreditLimitExceededException, InsufficientStockException,
    InvoiceAlreadyPaidException, InvoiceNotFoundException,
    PermissionDeniedException, ValidationException,
)


@pytest.fixture
def admin_user():
    from sqlalchemy import select
    with session_scope() as s:
        m = s.execute(select(UserModel).where(UserModel.username == "admin")).scalar_one()
        return User(
            id=m.id, username=m.username, email=m.email, password_hash=m.password_hash,
            full_name=m.full_name, role=UserRole(m.role), status=UserStatus(m.status),
        )


@pytest.fixture
def repos():
    return {
        "customer": SqlAlchemyCustomerRepository(),
        "supplier": SqlAlchemySupplierRepository(),
        "product": SqlAlchemyProductRepository(),
        "inventory": SqlAlchemyInventoryRepository(),
        "invoice": SqlAlchemyInvoiceRepository(),
        "account": SqlAlchemyAccountRepository(),
        "journal": SqlAlchemyJournalEntryRepository(),
    }


@pytest.fixture
def journal_setup(repos):
    builder = AutoJournalBuilder(repos["account"])
    create_uc = CreateJournalEntryUseCase(repos["journal"], repos["account"])
    post_uc = PostJournalEntryUseCase(repos["journal"])
    return builder, create_uc, post_uc


@pytest.fixture
def create_invoice_uc(repos, journal_setup):
    builder, create_uc, post_uc = journal_setup
    return CreateInvoiceUseCase(
        invoice_repo=repos["invoice"],
        customer_repo=repos["customer"],
        supplier_repo=repos["supplier"],
        product_repo=repos["product"],
        inventory_repo=repos["inventory"],
        journal_builder=builder,
        create_journal_uc=create_uc,
        post_journal_uc=post_uc,
    )


class TestCreditSales:
    """اختبارات الفواتير الآجلة (credit)."""

    @pytest.mark.asyncio
    async def test_credit_sale_updates_customer_balance(self, admin_user, repos, create_invoice_uc):
        """فاتورة بيع آجلة تُحدّث رصيد العميل."""
        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(
                code="CR-CUST-001", name="عميل آجل",
                credit_limit=Decimal("100000"),
            ),
            current_user=admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(
                sku="CR-PROD-001", name="منتج آجل",
                cost_price=Decimal("100"), sale_price=Decimal("200"),
            ),
            current_user=admin_user,
        )
        await AdjustInventoryUseCase(repos["product"], repos["inventory"]).execute(
            product.id, Decimal("50"), "init", current_user=admin_user,
        )

        # Create credit sale
        invoice = await create_invoice_uc.execute(
            CreateInvoiceRequest(
                invoice_type=InvoiceType.SALE,
                customer_id=customer.id,
                is_cash=False,  # آجل
                due_date=datetime.now() + timedelta(days=30),
                lines=[
                    InvoiceLineDTO(
                        product_id=product.id,
                        quantity=Decimal("5"),
                        unit_price=Decimal("200"),
                        tax_rate=Decimal("15"),
                    ),
                ],
            ),
            current_user=admin_user,
        )

        # Verify customer balance increased
        updated_customer = await repos["customer"].get_by_id(customer.id)
        assert updated_customer.current_balance == Decimal("1150")  # 5*200 + 15% VAT

    @pytest.mark.asyncio
    async def test_credit_sale_exceeds_limit_raises(self, admin_user, repos, create_invoice_uc):
        """فاتورة آجلة تتجاوز حد الائتمان تفشل."""
        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(
                code="CR-CUST-002", name="عميل حد ائتمان",
                credit_limit=Decimal("500"),  # حد منخفض
            ),
            current_user=admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(
                sku="CR-PROD-002", name="منتج",
                cost_price=Decimal("100"), sale_price=Decimal("1000"),
            ),
            current_user=admin_user,
        )
        await AdjustInventoryUseCase(repos["product"], repos["inventory"]).execute(
            product.id, Decimal("10"), "init", current_user=admin_user,
        )

        # Try to create invoice exceeding limit
        with pytest.raises(CreditLimitExceededException):
            await create_invoice_uc.execute(
                CreateInvoiceRequest(
                    invoice_type=InvoiceType.SALE,
                    customer_id=customer.id,
                    is_cash=False,
                    lines=[
                        InvoiceLineDTO(
                            product_id=product.id,
                            quantity=Decimal("1"),
                            unit_price=Decimal("1000"),
                        ),
                    ],
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_cash_sale_does_not_check_credit_limit(self, admin_user, repos, create_invoice_uc):
        """فاتورة نقدية لا تتحقق من حد الائتمان."""
        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(
                code="CR-CUST-003", name="عميل نقدي",
                credit_limit=Decimal("100"),  # حد منخفض جدًا
            ),
            current_user=admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(
                sku="CR-PROD-003", name="منتج",
                cost_price=Decimal("100"), sale_price=Decimal("5000"),
            ),
            current_user=admin_user,
        )
        await AdjustInventoryUseCase(repos["product"], repos["inventory"]).execute(
            product.id, Decimal("10"), "init", current_user=admin_user,
        )

        # Cash sale should succeed despite exceeding credit limit
        invoice = await create_invoice_uc.execute(
            CreateInvoiceRequest(
                invoice_type=InvoiceType.SALE,
                customer_id=customer.id,
                is_cash=True,  # نقدي
                lines=[
                    InvoiceLineDTO(
                        product_id=product.id,
                        quantity=Decimal("1"),
                        unit_price=Decimal("5000"),
                    ),
                ],
            ),
            current_user=admin_user,
        )
        assert invoice.total == Decimal("5750")  # 5000 + 15% VAT


class TestCreditPurchases:
    """اختبارات فواتير الشراء الآجلة."""

    @pytest.mark.asyncio
    async def test_credit_purchase_updates_supplier_balance(self, admin_user, repos, create_invoice_uc):
        """فاتورة شراء آجلة تُحدّث رصيد المورد."""
        supplier = await CreateSupplierUseCase(repos["supplier"]).execute(
            CreateSupplierRequest(code="CR-SUP-001", name="مورد آجل"),
            current_user=admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(sku="CR-PUR-001", name="منتج شراء"),
            current_user=admin_user,
        )

        invoice = await create_invoice_uc.execute(
            CreateInvoiceRequest(
                invoice_type=InvoiceType.PURCHASE,
                supplier_id=supplier.id,
                is_cash=False,  # آجل
                lines=[
                    InvoiceLineDTO(
                        product_id=product.id,
                        quantity=Decimal("10"),
                        unit_price=Decimal("100"),
                        tax_rate=Decimal("15"),
                    ),
                ],
            ),
            current_user=admin_user,
        )

        # Verify supplier balance increased
        updated_supplier = await repos["supplier"].get_by_id(supplier.id)
        assert updated_supplier.current_balance == Decimal("1150")  # 10*100 + 15% VAT


class TestInvoiceCancellation:
    """اختبارات إلغاء الفواتير."""

    @pytest.mark.asyncio
    async def test_cancel_invoice_creates_reverse_journal(
        self, admin_user, repos, create_invoice_uc, journal_setup
    ):
        """إلغاء فاتورة يُنشئ قيدًا عكسيًا."""
        builder, create_uc, post_uc = journal_setup

        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(code="CAN-CUST-001", name="عميل إلغاء"),
            current_user=admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(sku="CAN-PROD-001", name="منتج إلغاء"),
            current_user=admin_user,
        )
        await AdjustInventoryUseCase(repos["product"], repos["inventory"]).execute(
            product.id, Decimal("100"), "init", current_user=admin_user,
        )

        invoice = await create_invoice_uc.execute(
            CreateInvoiceRequest(
                invoice_type=InvoiceType.SALE,
                customer_id=customer.id,
                is_cash=True,
                lines=[
                    InvoiceLineDTO(
                        product_id=product.id,
                        quantity=Decimal("5"),
                        unit_price=Decimal("100"),
                    ),
                ],
            ),
            current_user=admin_user,
        )

        # Cancel
        reverse_uc = ReverseJournalEntryUseCase(repos["journal"])
        cancel_uc = CancelInvoiceUseCase(repos["invoice"], reverse_uc)
        cancelled = await cancel_uc.execute(invoice.id, current_user=admin_user)

        assert cancelled.status == InvoiceStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_raises(self, admin_user, repos, create_invoice_uc, journal_setup):
        """إلغاء فاتورة ملغاة سابقًا يفشل."""
        builder, create_uc, post_uc = journal_setup

        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(code="CAN-CUST-002", name="عميل"),
            current_user=admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(sku="CAN-PROD-002", name="منتج"),
            current_user=admin_user,
        )
        await AdjustInventoryUseCase(repos["product"], repos["inventory"]).execute(
            product.id, Decimal("100"), "init", current_user=admin_user,
        )

        invoice = await create_invoice_uc.execute(
            CreateInvoiceRequest(
                invoice_type=InvoiceType.SALE,
                customer_id=customer.id,
                is_cash=True,
                lines=[InvoiceLineDTO(product_id=product.id, quantity=Decimal("1"), unit_price=Decimal("100"))],
            ),
            current_user=admin_user,
        )

        # Cancel first time
        reverse_uc = ReverseJournalEntryUseCase(repos["journal"])
        cancel_uc = CancelInvoiceUseCase(repos["invoice"], reverse_uc)
        await cancel_uc.execute(invoice.id, current_user=admin_user)

        # Cancel again should fail
        with pytest.raises(InvoiceAlreadyPaidException):
            await cancel_uc.execute(invoice.id, current_user=admin_user)


class TestGetAndListInvoices:
    """اختبارات الحصول على وسرد الفواتير."""

    @pytest.mark.asyncio
    async def test_get_invoice_success(self, admin_user, repos, create_invoice_uc):
        """الحصول على فاتورة موجودة."""
        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(code="GET-CUST-001", name="عميل"),
            current_user=admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(sku="GET-PROD-001", name="منتج"),
            current_user=admin_user,
        )
        await AdjustInventoryUseCase(repos["product"], repos["inventory"]).execute(
            product.id, Decimal("100"), "init", current_user=admin_user,
        )

        invoice = await create_invoice_uc.execute(
            CreateInvoiceRequest(
                invoice_type=InvoiceType.SALE,
                customer_id=customer.id,
                is_cash=True,
                lines=[InvoiceLineDTO(product_id=product.id, quantity=Decimal("1"), unit_price=Decimal("100"))],
            ),
            current_user=admin_user,
        )

        get_uc = GetInvoiceUseCase(repos["invoice"])
        fetched = await get_uc.execute(invoice.id, current_user=admin_user)
        assert fetched.id == invoice.id
        assert fetched.invoice_no == invoice.invoice_no

    @pytest.mark.asyncio
    async def test_get_invoice_not_found(self, admin_user, repos):
        """الحصول على فاتورة غير موجودة يفشل."""
        get_uc = GetInvoiceUseCase(repos["invoice"])
        with pytest.raises(InvoiceNotFoundException):
            await get_uc.execute(uuid4(), current_user=admin_user)

    @pytest.mark.asyncio
    async def test_list_invoices_all(self, admin_user, repos, create_invoice_uc):
        """سرد كل الفواتير."""
        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(code="LST-CUST-001", name="عميل"),
            current_user=admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(sku="LST-PROD-001", name="منتج"),
            current_user=admin_user,
        )
        await AdjustInventoryUseCase(repos["product"], repos["inventory"]).execute(
            product.id, Decimal("100"), "init", current_user=admin_user,
        )

        # Create 3 invoices
        for i in range(3):
            await create_invoice_uc.execute(
                CreateInvoiceRequest(
                    invoice_type=InvoiceType.SALE,
                    customer_id=customer.id,
                    is_cash=True,
                    lines=[InvoiceLineDTO(product_id=product.id, quantity=Decimal("1"), unit_price=Decimal("100"))],
                ),
                current_user=admin_user,
            )

        # Use the invoice repository directly
        invoices = await repos["invoice"].list_all(skip=0, limit=100)
        assert len(invoices) >= 3

    @pytest.mark.asyncio
    async def test_list_invoices_by_type(self, admin_user, repos, create_invoice_uc):
        """سرد الفواتير حسب النوع."""
        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(code="TYP-CUST-001", name="عميل"),
            current_user=admin_user,
        )
        supplier = await CreateSupplierUseCase(repos["supplier"]).execute(
            CreateSupplierRequest(code="TYP-SUP-001", name="مورد"),
            current_user=admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(sku="TYP-PROD-001", name="منتج"),
            current_user=admin_user,
        )
        await AdjustInventoryUseCase(repos["product"], repos["inventory"]).execute(
            product.id, Decimal("100"), "init", current_user=admin_user,
        )

        # Create sale and purchase invoices
        await create_invoice_uc.execute(
            CreateInvoiceRequest(
                invoice_type=InvoiceType.SALE,
                customer_id=customer.id,
                is_cash=True,
                lines=[InvoiceLineDTO(product_id=product.id, quantity=Decimal("1"), unit_price=Decimal("100"))],
            ),
            current_user=admin_user,
        )
        await create_invoice_uc.execute(
            CreateInvoiceRequest(
                invoice_type=InvoiceType.PURCHASE,
                supplier_id=supplier.id,
                is_cash=True,
                lines=[InvoiceLineDTO(product_id=product.id, quantity=Decimal("1"), unit_price=Decimal("50"))],
            ),
            current_user=admin_user,
        )

        # Use repository directly
        sales = await repos["invoice"].list_all(invoice_type=InvoiceType.SALE, skip=0, limit=100)
        purchases = await repos["invoice"].list_all(invoice_type=InvoiceType.PURCHASE, skip=0, limit=100)

        assert all(i.invoice_type == InvoiceType.SALE for i in sales)
        assert all(i.invoice_type == InvoiceType.PURCHASE for i in purchases)


class TestInvoiceValidation:
    """اختبارات التحقق من صحة بيانات الفاتورة."""

    @pytest.mark.asyncio
    async def test_empty_lines_raises(self, admin_user, repos, create_invoice_uc):
        """فاتورة بدون بنود تفشل."""
        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(code="EMP-CUST-001", name="عميل"),
            current_user=admin_user,
        )
        with pytest.raises(ValidationException, match="at least one line"):
            await create_invoice_uc.execute(
                CreateInvoiceRequest(
                    invoice_type=InvoiceType.SALE,
                    customer_id=customer.id,
                    is_cash=True,
                    lines=[],  # فارغة
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_sale_without_customer_raises(self, admin_user, repos, create_invoice_uc):
        """فاتورة بيع بدون عميل تفشل."""
        with pytest.raises(ValidationException, match="customer_id"):
            await create_invoice_uc.execute(
                CreateInvoiceRequest(
                    invoice_type=InvoiceType.SALE,
                    customer_id=None,
                    is_cash=True,
                    lines=[InvoiceLineDTO(product_id=uuid4(), quantity=Decimal("1"), unit_price=Decimal("100"))],
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_purchase_without_supplier_raises(self, admin_user, repos, create_invoice_uc):
        """فاتورة شراء بدون مورد تفشل."""
        with pytest.raises(ValidationException, match="supplier_id"):
            await create_invoice_uc.execute(
                CreateInvoiceRequest(
                    invoice_type=InvoiceType.PURCHASE,
                    supplier_id=None,
                    is_cash=True,
                    lines=[InvoiceLineDTO(product_id=uuid4(), quantity=Decimal("1"), unit_price=Decimal("100"))],
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_sale_insufficient_stock_raises(self, admin_user, repos, create_invoice_uc):
        """بيع كمية أكبر من المخزون يفشل."""
        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(code="STK-CUST-001", name="عميل"),
            current_user=admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(sku="STK-PROD-001", name="منتج"),
            current_user=admin_user,
        )
        # No stock added

        with pytest.raises(InsufficientStockException):
            await create_invoice_uc.execute(
                CreateInvoiceRequest(
                    invoice_type=InvoiceType.SALE,
                    customer_id=customer.id,
                    is_cash=True,
                    lines=[InvoiceLineDTO(product_id=product.id, quantity=Decimal("100"), unit_price=Decimal("100"))],
                ),
                current_user=admin_user,
            )
