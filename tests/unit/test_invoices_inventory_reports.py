"""
اختبارات الفواتير والمخزون والتقارير
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
    CreateProductUseCase, CreateProductRequest,
    GetProductBalanceUseCase, ListInventoryEntriesUseCase, AdjustInventoryUseCase,
)
from use_cases.invoices.invoice_use_cases import (
    CreateInvoiceUseCase, CreateInvoiceRequest, InvoiceLineDTO,
    calculate_invoice_totals,
)
from use_cases.journal.journal_use_cases import (
    AutoJournalBuilder, CreateJournalEntryUseCase, PostJournalEntryUseCase,
    ReverseJournalEntryUseCase,
)
from use_cases.reports.report_use_cases import (
    GenerateTrialBalanceUseCase, GenerateBalanceSheetUseCase,
    GenerateIncomeStatementUseCase,
)
from domain.entities.user import User, UserStatus
from domain.entities.invoice import InvoiceType
from domain.entities.product import InventoryEntry
from domain.value_objects.value_objects import UserRole
from domain.exceptions.exceptions import InsufficientStockException


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
    """All repositories wired up."""
    customer_repo = SqlAlchemyCustomerRepository()
    supplier_repo = SqlAlchemySupplierRepository()
    product_repo = SqlAlchemyProductRepository()
    inventory_repo = SqlAlchemyInventoryRepository()
    invoice_repo = SqlAlchemyInvoiceRepository()
    account_repo = SqlAlchemyAccountRepository()
    journal_repo = SqlAlchemyJournalEntryRepository()
    return {
        "customer": customer_repo,
        "supplier": supplier_repo,
        "product": product_repo,
        "inventory": inventory_repo,
        "invoice": invoice_repo,
        "account": account_repo,
        "journal": journal_repo,
    }


class TestInvoiceCalculations:
    """اختبارات حسابات الفاتورة."""

    def test_simple_totals(self):
        lines = [
            InvoiceLineDTO(
                product_id=uuid4(),
                quantity=Decimal("2"),
                unit_price=Decimal("100"),
                tax_rate=Decimal("15"),
            ),
        ]
        totals = calculate_invoice_totals(lines)
        # subtotal = 200, tax = 30, total = 230
        assert totals.subtotal == Decimal("200")
        assert totals.tax_amount == Decimal("30")
        assert totals.total == Decimal("230")

    def test_with_discount(self):
        lines = [
            InvoiceLineDTO(
                product_id=uuid4(),
                quantity=Decimal("1"),
                unit_price=Decimal("100"),
                tax_rate=Decimal("15"),
                discount=Decimal("20"),
            ),
        ]
        totals = calculate_invoice_totals(lines)
        # subtotal = 100 - 20 = 80, tax = 80 * 0.15 = 12, total = 92
        assert totals.subtotal == Decimal("80")
        assert totals.tax_amount == Decimal("12")
        assert totals.total == Decimal("92")
        assert totals.discount_total == Decimal("20")

    def test_multiple_lines(self):
        lines = [
            InvoiceLineDTO(product_id=uuid4(), quantity=Decimal("3"), unit_price=Decimal("50"), tax_rate=Decimal("15")),
            InvoiceLineDTO(product_id=uuid4(), quantity=Decimal("2"), unit_price=Decimal("100"), tax_rate=Decimal("15")),
        ]
        totals = calculate_invoice_totals(lines)
        # subtotal = 150 + 200 = 350, tax = 52.5, total = 402.5
        assert totals.subtotal == Decimal("350")
        assert totals.tax_amount == Decimal("52.5")

    def test_negative_quantity_raises(self):
        lines = [InvoiceLineDTO(product_id=uuid4(), quantity=Decimal("-1"), unit_price=Decimal("100"))]
        with pytest.raises(Exception, match="must be positive"):
            calculate_invoice_totals(lines)


class TestProductAndInventory:
    """اختبارات المنتجات والمخزون."""

    @pytest.mark.asyncio
    async def test_create_product(self, admin_user, repos):
        uc = CreateProductUseCase(repos["product"])
        req = CreateProductRequest(
            sku="PROD-001",
            name="لابتوب Dell",
            barcode="1234567890",
            cost_price=Decimal("2000"),
            sale_price=Decimal("2500"),
            tax_rate=Decimal("15"),
            min_stock_level=Decimal("5"),
        )
        product = await uc.execute(req, admin_user)
        assert product.sku == "PROD-001"
        assert product.sale_price == Decimal("2500")
        assert product.profit_margin() == Decimal("25")

    @pytest.mark.asyncio
    async def test_inventory_balance_zero_initially(self, admin_user, repos):
        # Create a product
        create_uc = CreateProductUseCase(repos["product"])
        product = await create_uc.execute(
            CreateProductRequest(sku="PROD-BAL-001", name="Test Product"),
            admin_user,
        )
        balance_uc = GetProductBalanceUseCase(repos["inventory"])
        balance = await balance_uc.execute(product.id, admin_user)
        assert balance == 0.0

    @pytest.mark.asyncio
    async def test_inventory_adjustment_in(self, admin_user, repos):
        create_uc = CreateProductUseCase(repos["product"])
        product = await create_uc.execute(
            CreateProductRequest(sku="PROD-ADJ-001", name="Adjustment Test"),
            admin_user,
        )
        # Adjust to 50
        adjust_uc = AdjustInventoryUseCase(repos["product"], repos["inventory"])
        entry = await adjust_uc.execute(
            product.id, Decimal("50"), "initial stock", admin_user,
        )
        assert entry.quantity_in == Decimal("50")

        # Verify balance
        balance_uc = GetProductBalanceUseCase(repos["inventory"])
        balance = await balance_uc.execute(product.id, admin_user)
        assert balance == 50.0

    @pytest.mark.asyncio
    async def test_inventory_entries_list(self, admin_user, repos):
        create_uc = CreateProductUseCase(repos["product"])
        product = await create_uc.execute(
            CreateProductRequest(sku="PROD-LIST-001", name="List Test"),
            admin_user,
        )
        # Add some entries
        adjust_uc = AdjustInventoryUseCase(repos["product"], repos["inventory"])
        await adjust_uc.execute(product.id, Decimal("100"), "first", admin_user)
        await adjust_uc.execute(product.id, Decimal("80"), "second (after selling)", admin_user)

        list_uc = ListInventoryEntriesUseCase(repos["inventory"])
        entries = await list_uc.execute(product.id, admin_user)
        assert len(entries) >= 2


class TestInvoiceCreation:
    """اختبارات إنشاء الفواتير."""

    @pytest.mark.asyncio
    async def test_create_sales_invoice_with_journal(self, admin_user, repos):
        # Setup: customer + product + stock
        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(code="INV-CUST-001", name="عميل الفاتورة"),
            admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(
                sku="INV-PROD-001", name="منتج الفاتورة",
                cost_price=Decimal("100"), sale_price=Decimal("150"),
            ),
            admin_user,
        )
        # Add stock
        await AdjustInventoryUseCase(repos["product"], repos["inventory"]).execute(
            product.id, Decimal("100"), "initial stock", admin_user,
        )

        # Build dependencies for invoice use case
        journal_builder = AutoJournalBuilder(repos["account"])
        create_journal_uc = CreateJournalEntryUseCase(repos["journal"], repos["account"])
        post_journal_uc = PostJournalEntryUseCase(repos["journal"])

        create_invoice_uc = CreateInvoiceUseCase(
            invoice_repo=repos["invoice"],
            customer_repo=repos["customer"],
            supplier_repo=repos["supplier"],
            product_repo=repos["product"],
            inventory_repo=repos["inventory"],
            journal_builder=journal_builder,
            create_journal_uc=create_journal_uc,
            post_journal_uc=post_journal_uc,
        )

        # Create cash sale invoice
        request = CreateInvoiceRequest(
            invoice_type=InvoiceType.SALE,
            customer_id=customer.id,
            is_cash=True,
            lines=[
                InvoiceLineDTO(
                    product_id=product.id,
                    quantity=Decimal("5"),
                    unit_price=Decimal("150"),
                    tax_rate=Decimal("15"),
                ),
            ],
        )
        invoice = await create_invoice_uc.execute(request, admin_user)

        # Verify invoice
        assert invoice.invoice_no.startswith("INV-S-")
        assert invoice.subtotal == Decimal("750")  # 5 * 150
        assert invoice.tax_amount == Decimal("112.5")
        assert invoice.total == Decimal("862.5")
        assert invoice.journal_entry_id is not None

        # Verify inventory decreased
        balance_uc = GetProductBalanceUseCase(repos["inventory"])
        balance = await balance_uc.execute(product.id, admin_user)
        assert balance == 95.0  # 100 - 5

    @pytest.mark.asyncio
    async def test_sale_insufficient_stock_raises(self, admin_user, repos):
        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(code="INV-CUST-002", name="Customer 2"),
            admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(sku="INV-PROD-002", name="Product 2"),
            admin_user,
        )
        # No stock added - should fail

        journal_builder = AutoJournalBuilder(repos["account"])
        create_journal_uc = CreateJournalEntryUseCase(repos["journal"], repos["account"])
        post_journal_uc = PostJournalEntryUseCase(repos["journal"])

        create_invoice_uc = CreateInvoiceUseCase(
            invoice_repo=repos["invoice"],
            customer_repo=repos["customer"],
            supplier_repo=repos["supplier"],
            product_repo=repos["product"],
            inventory_repo=repos["inventory"],
            journal_builder=journal_builder,
            create_journal_uc=create_journal_uc,
            post_journal_uc=post_journal_uc,
        )

        request = CreateInvoiceRequest(
            invoice_type=InvoiceType.SALE,
            customer_id=customer.id,
            is_cash=True,
            lines=[InvoiceLineDTO(product_id=product.id, quantity=Decimal("10"), unit_price=Decimal("100"))],
        )
        with pytest.raises(InsufficientStockException):
            await create_invoice_uc.execute(request, admin_user)

    @pytest.mark.asyncio
    async def test_create_purchase_invoice(self, admin_user, repos):
        supplier = await CreateSupplierUseCase(repos["supplier"]).execute(
            CreateSupplierRequest(code="INV-SUP-001", name="مورد الفاتورة"),
            admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(sku="INV-PUR-001", name="منتج الشراء"),
            admin_user,
        )

        journal_builder = AutoJournalBuilder(repos["account"])
        create_journal_uc = CreateJournalEntryUseCase(repos["journal"], repos["account"])
        post_journal_uc = PostJournalEntryUseCase(repos["journal"])

        create_invoice_uc = CreateInvoiceUseCase(
            invoice_repo=repos["invoice"],
            customer_repo=repos["customer"],
            supplier_repo=repos["supplier"],
            product_repo=repos["product"],
            inventory_repo=repos["inventory"],
            journal_builder=journal_builder,
            create_journal_uc=create_journal_uc,
            post_journal_uc=post_journal_uc,
        )

        request = CreateInvoiceRequest(
            invoice_type=InvoiceType.PURCHASE,
            supplier_id=supplier.id,
            is_cash=True,
            lines=[
                InvoiceLineDTO(
                    product_id=product.id,
                    quantity=Decimal("20"),
                    unit_price=Decimal("50"),
                    tax_rate=Decimal("15"),
                ),
            ],
        )
        invoice = await create_invoice_uc.execute(request, admin_user)
        assert invoice.invoice_no.startswith("INV-P-")
        assert invoice.total == Decimal("1150")  # 1000 + 150 VAT

        # Verify inventory increased
        balance_uc = GetProductBalanceUseCase(repos["inventory"])
        balance = await balance_uc.execute(product.id, admin_user)
        assert balance == 20.0


class TestReports:
    """اختبارات التقارير."""

    @pytest.mark.asyncio
    async def test_trial_balance(self, admin_user, repos):
        uc = GenerateTrialBalanceUseCase()
        report = await uc.execute(datetime.utcnow(), admin_user)
        assert report.is_balanced is True  # Always balanced for double-entry
        assert isinstance(report.lines, list)

    @pytest.mark.asyncio
    async def test_balance_sheet(self, admin_user, repos):
        uc = GenerateBalanceSheetUseCase()
        report = await uc.execute(datetime.utcnow(), admin_user)
        # Note: Before closing entries, A ≠ L + E (because revenues/expenses
        # are not yet transferred to retained earnings). The check here is
        # structural correctness, not strict balance.
        assert isinstance(report.assets, list)
        assert isinstance(report.liabilities, list)
        assert isinstance(report.equity, list)
        assert report.total_assets == sum((a.amount for a in report.assets), Decimal("0"))
        assert report.total_liabilities == sum((l.amount for l in report.liabilities), Decimal("0"))
        assert report.total_equity == sum((e.amount for e in report.equity), Decimal("0"))

    @pytest.mark.asyncio
    async def test_income_statement(self, admin_user, repos):
        uc = GenerateIncomeStatementUseCase()
        start = datetime.utcnow() - timedelta(days=30)
        end = datetime.utcnow()
        report = await uc.execute(start, end, admin_user)
        assert isinstance(report.revenues, list)
        assert isinstance(report.expenses, list)
        assert report.net_income == report.total_revenue - report.total_expense
