"""
اختبارات المرتجعات والمصروفات
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
    CreateProductUseCase, CreateProductRequest, AdjustInventoryUseCase,
)
from use_cases.invoices.invoice_use_cases import (
    CreateInvoiceUseCase, CreateInvoiceRequest, InvoiceLineDTO,
)
from use_cases.invoices.returns_use_cases import CreateReturnUseCase, CreateReturnRequest
from use_cases.journal.expenses_use_cases import (
    RecordExpenseUseCase, RecordExpenseRequest,
    RecordRevenueUseCase, RecordRevenueRequest,
)
from use_cases.journal.journal_use_cases import (
    AutoJournalBuilder, CreateJournalEntryUseCase, PostJournalEntryUseCase,
)
from domain.entities.user import User, UserStatus
from domain.entities.invoice import InvoiceType
from domain.value_objects.value_objects import UserRole


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
    """Setup common journal use cases."""
    builder = AutoJournalBuilder(repos["account"])
    create_uc = CreateJournalEntryUseCase(repos["journal"], repos["account"])
    post_uc = PostJournalEntryUseCase(repos["journal"])
    return builder, create_uc, post_uc


class TestReturns:
    """اختبارات المرتجعات."""

    @pytest.mark.asyncio
    async def test_create_sale_return(self, admin_user, repos, journal_setup):
        """اختبار مرتجع بيع كامل: إنشاء فاتورة بيع ثم مرتجع لها."""
        builder, create_uc, post_uc = journal_setup

        # Setup: customer + product + stock
        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(code="RET-CUST-001", name="عميل المرتجع"),
            admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(
                sku="RET-PROD-001", name="منتج المرتجع",
                cost_price=Decimal("100"), sale_price=Decimal("200"),
            ),
            admin_user,
        )
        await AdjustInventoryUseCase(repos["product"], repos["inventory"]).execute(
            product.id, Decimal("50"), "initial", admin_user,
        )

        # Create original sale invoice (10 units)
        create_invoice_uc = CreateInvoiceUseCase(
            invoice_repo=repos["invoice"],
            customer_repo=repos["customer"],
            supplier_repo=repos["supplier"],
            product_repo=repos["product"],
            inventory_repo=repos["inventory"],
            journal_builder=builder,
            create_journal_uc=create_uc,
            post_journal_uc=post_uc,
        )
        original_invoice = await create_invoice_uc.execute(
            CreateInvoiceRequest(
                invoice_type=InvoiceType.SALE,
                customer_id=customer.id,
                is_cash=True,
                lines=[
                    InvoiceLineDTO(
                        product_id=product.id,
                        quantity=Decimal("10"),
                        unit_price=Decimal("200"),
                        tax_rate=Decimal("15"),
                    ),
                ],
            ),
            admin_user,
        )
        # Verify stock decreased to 40
        balance_before_return = await repos["inventory"].get_balance(product.id)
        assert balance_before_return == 40.0

        # Create sale return (3 units)
        create_return_uc = CreateReturnUseCase(
            invoice_repo=repos["invoice"],
            customer_repo=repos["customer"],
            supplier_repo=repos["supplier"],
            product_repo=repos["product"],
            inventory_repo=repos["inventory"],
            journal_builder=builder,
            create_journal_uc=create_uc,
            post_journal_uc=post_uc,
        )
        return_invoice = await create_return_uc.execute(
            CreateReturnRequest(
                original_invoice_id=original_invoice.id,
                lines=[
                    InvoiceLineDTO(
                        product_id=product.id,
                        quantity=Decimal("3"),
                        unit_price=Decimal("200"),
                        tax_rate=Decimal("15"),
                    ),
                ],
                reason="منتج معيب",
                is_cash=True,
            ),
            admin_user,
        )

        # Verify
        assert return_invoice.invoice_no.startswith("RET-S-")
        assert return_invoice.invoice_type == InvoiceType.SALE_RETURN
        # Subtotal: 3 * 200 = 600, tax: 90, total: 690
        assert return_invoice.subtotal == Decimal("600")
        assert return_invoice.tax_amount == Decimal("90")
        assert return_invoice.total == Decimal("690")
        assert return_invoice.journal_entry_id is not None

        # Verify stock increased back to 43 (40 + 3 returned)
        balance_after_return = await repos["inventory"].get_balance(product.id)
        assert balance_after_return == 43.0

    @pytest.mark.asyncio
    async def test_create_purchase_return(self, admin_user, repos, journal_setup):
        """اختبار مرتجع شراء."""
        builder, create_uc, post_uc = journal_setup

        supplier = await CreateSupplierUseCase(repos["supplier"]).execute(
            CreateSupplierRequest(code="RET-SUP-001", name="مورد المرتجع"),
            admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(
                sku="RET-PROD-002", name="منتج الشراء المرتجع",
                cost_price=Decimal("50"), sale_price=Decimal("80"),
            ),
            admin_user,
        )

        # Create original purchase invoice (20 units)
        create_invoice_uc = CreateInvoiceUseCase(
            invoice_repo=repos["invoice"],
            customer_repo=repos["customer"],
            supplier_repo=repos["supplier"],
            product_repo=repos["product"],
            inventory_repo=repos["inventory"],
            journal_builder=builder,
            create_journal_uc=create_uc,
            post_journal_uc=post_uc,
        )
        original = await create_invoice_uc.execute(
            CreateInvoiceRequest(
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
            ),
            admin_user,
        )
        # Stock should be 20
        assert await repos["inventory"].get_balance(product.id) == 20.0

        # Create purchase return (5 units)
        create_return_uc = CreateReturnUseCase(
            invoice_repo=repos["invoice"],
            customer_repo=repos["customer"],
            supplier_repo=repos["supplier"],
            product_repo=repos["product"],
            inventory_repo=repos["inventory"],
            journal_builder=builder,
            create_journal_uc=create_uc,
            post_journal_uc=post_uc,
        )
        return_inv = await create_return_uc.execute(
            CreateReturnRequest(
                original_invoice_id=original.id,
                lines=[
                    InvoiceLineDTO(
                        product_id=product.id,
                        quantity=Decimal("5"),
                        unit_price=Decimal("50"),
                        tax_rate=Decimal("15"),
                    ),
                ],
                reason="بضاعة غير مطابقة",
                is_cash=True,
            ),
            admin_user,
        )

        assert return_inv.invoice_no.startswith("RET-P-")
        assert return_inv.invoice_type == InvoiceType.PURCHASE_RETURN
        # Stock should be 15 (20 - 5 returned to supplier)
        assert await repos["inventory"].get_balance(product.id) == 15.0

    @pytest.mark.asyncio
    async def test_return_quantity_exceeds_original_raises(self, admin_user, repos, journal_setup):
        """لا يمكن إرجاع كمية أكبر من الأصلية."""
        builder, create_uc, post_uc = journal_setup

        customer = await CreateCustomerUseCase(repos["customer"]).execute(
            CreateCustomerRequest(code="RET-CUST-002", name="Customer 2"),
            admin_user,
        )
        product = await CreateProductUseCase(repos["product"]).execute(
            CreateProductRequest(sku="RET-PROD-003", name="Product 3"),
            admin_user,
        )
        await AdjustInventoryUseCase(repos["product"], repos["inventory"]).execute(
            product.id, Decimal("100"), "init", admin_user,
        )

        create_invoice_uc = CreateInvoiceUseCase(
            invoice_repo=repos["invoice"],
            customer_repo=repos["customer"],
            supplier_repo=repos["supplier"],
            product_repo=repos["product"],
            inventory_repo=repos["inventory"],
            journal_builder=builder,
            create_journal_uc=create_uc,
            post_journal_uc=post_uc,
        )
        original = await create_invoice_uc.execute(
            CreateInvoiceRequest(
                invoice_type=InvoiceType.SALE,
                customer_id=customer.id,
                is_cash=True,
                lines=[InvoiceLineDTO(product_id=product.id, quantity=Decimal("5"), unit_price=Decimal("100"))],
            ),
            admin_user,
        )

        # Try to return 10 (more than 5)
        create_return_uc = CreateReturnUseCase(
            invoice_repo=repos["invoice"],
            customer_repo=repos["customer"],
            supplier_repo=repos["supplier"],
            product_repo=repos["product"],
            inventory_repo=repos["inventory"],
            journal_builder=builder,
            create_journal_uc=create_uc,
            post_journal_uc=post_uc,
        )
        from domain.exceptions.exceptions import ValidationException
        with pytest.raises(ValidationException, match="exceeds original"):
            await create_return_uc.execute(
                CreateReturnRequest(
                    original_invoice_id=original.id,
                    lines=[InvoiceLineDTO(product_id=product.id, quantity=Decimal("10"), unit_price=Decimal("100"))],
                ),
                admin_user,
            )


class TestExpensesAndRevenues:
    """اختبارات المصروفات والإيرادات."""

    @pytest.mark.asyncio
    async def test_record_expense(self, admin_user, repos, journal_setup):
        """تسجيل مصروف كهرباء 800 ر.س من الصندوق."""
        builder, create_uc, post_uc = journal_setup

        uc = RecordExpenseUseCase(
            account_repo=repos["account"],
            journal_builder=builder,
            create_journal_uc=create_uc,
            post_journal_uc=post_uc,
        )
        entry_no = await uc.execute(
            RecordExpenseRequest(
                description="فاتورة كهرباء المكتب",
                expense_account_code="5203",  # كهرباء وماء
                amount=Decimal("800"),
                payment_account_code="1101",  # الصندوق
                is_cash=True,
            ),
            admin_user,
        )

        # Verify entry was created and posted
        entry = await repos["journal"].get_by_no(entry_no)
        assert entry is not None
        assert entry.is_balanced()
        # Debit: 800 (electricity expense)
        # Credit: 800 (cash)
        assert entry.total_debit() == Decimal("800")
        assert entry.total_credit() == Decimal("800")

    @pytest.mark.asyncio
    async def test_record_expense_invalid_account_raises(self, admin_user, repos, journal_setup):
        """حساب غير موجود يرمي استثناء."""
        builder, create_uc, post_uc = journal_setup

        uc = RecordExpenseUseCase(
            account_repo=repos["account"],
            journal_builder=builder,
            create_journal_uc=create_uc,
            post_journal_uc=post_uc,
        )
        from domain.exceptions.exceptions import AccountNotFoundException
        with pytest.raises(AccountNotFoundException):
            await uc.execute(
                RecordExpenseRequest(
                    description="test",
                    expense_account_code="9999",  # doesn't exist
                    amount=Decimal("100"),
                ),
                admin_user,
            )

    @pytest.mark.asyncio
    async def test_record_expense_negative_amount_raises(self, admin_user, repos, journal_setup):
        """المبلغ السالب مرفوض."""
        builder, create_uc, post_uc = journal_setup

        uc = RecordExpenseUseCase(
            account_repo=repos["account"],
            journal_builder=builder,
            create_journal_uc=create_uc,
            post_journal_uc=post_uc,
        )
        from domain.exceptions.exceptions import ValidationException
        with pytest.raises(ValidationException, match="must be positive"):
            await uc.execute(
                RecordExpenseRequest(
                    description="test",
                    expense_account_code="5201",
                    amount=Decimal("-100"),
                ),
                admin_user,
            )

    @pytest.mark.asyncio
    async def test_record_revenue(self, admin_user, repos, journal_setup):
        """تسجيل إيراد فوائد بنكية 500 ر.س."""
        builder, create_uc, post_uc = journal_setup

        uc = RecordRevenueUseCase(
            account_repo=repos["account"],
            journal_builder=builder,
            create_journal_uc=create_uc,
            post_journal_uc=post_uc,
        )
        entry_no = await uc.execute(
            RecordRevenueRequest(
                description="فوائد بنكية",
                revenue_account_code="4201",  # إيرادات الفوائد
                amount=Decimal("500"),
                receipt_account_code="1102",  # البنك
                is_cash=True,
            ),
            admin_user,
        )

        entry = await repos["journal"].get_by_no(entry_no)
        assert entry is not None
        assert entry.is_balanced()
        # Debit: 500 (bank)
        # Credit: 500 (interest income)
        assert entry.total_debit() == Decimal("500")
        assert entry.total_credit() == Decimal("500")

    @pytest.mark.asyncio
    async def test_record_expense_salary(self, admin_user, repos, journal_setup):
        """تسجيل مصروف رواتب 50000 ر.س من البنك."""
        builder, create_uc, post_uc = journal_setup

        uc = RecordExpenseUseCase(
            account_repo=repos["account"],
            journal_builder=builder,
            create_journal_uc=create_uc,
            post_journal_uc=post_uc,
        )
        entry_no = await uc.execute(
            RecordExpenseRequest(
                description="رواتب ديسمبر 2026",
                expense_account_code="5201",  # رواتب وأجور
                amount=Decimal("50000"),
                payment_account_code="1102",  # البنك
                is_cash=False,
            ),
            admin_user,
        )

        entry = await repos["journal"].get_by_no(entry_no)
        assert entry is not None
        assert entry.total_debit() == Decimal("50000")
        assert entry.total_credit() == Decimal("50000")
