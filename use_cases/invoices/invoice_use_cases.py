"""
Invoice Use Cases - حالات استخدام الفواتير

فواتير البيع والشراء والمرتجعات.
كل فاتورة تُولّد قيدًا محاسبيًا تلقائيًا وفق القواعد القياسية.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from domain.entities.invoice import (
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    InvoiceType,
)
from domain.entities.journal import JournalEntryReferenceType
from domain.exceptions.exceptions import (
    CreditLimitExceededException,
    CustomerNotFoundException,
    InsufficientStockException,
    InvoiceAlreadyPaidException,
    InvoiceNotFoundException,
    PermissionDeniedException,
    ProductNotFoundException,
    SupplierNotFoundException,
    ValidationException,
)
from domain.value_objects.value_objects import Permission
from use_cases.journal.journal_use_cases import (
    AutoJournalBuilder,
    CreateJournalEntryUseCase,
    PostJournalEntryUseCase,
)
from use_cases.repositories.interfaces import (
    ICustomerRepository,
    IInventoryRepository,
    IInvoiceRepository,
    IProductRepository,
    ISupplierRepository,
)


# ============================================================
# DTOs
# ============================================================
@dataclass
class InvoiceLineDTO:
    product_id: UUID
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal = Decimal("15")
    discount: Decimal = Decimal("0")
    description: str = ""


@dataclass
class CreateInvoiceRequest:
    invoice_type: InvoiceType
    customer_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    issue_date: datetime = field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    lines: list[InvoiceLineDTO] = field(default_factory=list)
    notes: str = ""
    is_cash: bool = False  # نقدي أم آجل


@dataclass
class InvoiceSummary:
    """ملخص حسابات الفاتورة."""

    subtotal: Decimal
    tax_amount: Decimal
    discount_total: Decimal
    total: Decimal

    def to_dict(self) -> dict:
        return {
            "subtotal": str(self.subtotal),
            "tax_amount": str(self.tax_amount),
            "discount_total": str(self.discount_total),
            "total": str(self.total),
        }


# ============================================================
# Helper: Calculate invoice totals
# ============================================================
def calculate_invoice_totals(lines: list[InvoiceLineDTO]) -> InvoiceSummary:
    """حساب الإجماليات (subtotal, tax, total)."""
    subtotal = Decimal("0")
    tax_amount = Decimal("0")
    discount_total = Decimal("0")

    for line in lines:
        if line.quantity <= 0:
            raise ValidationException("quantity", "must be positive")
        if line.unit_price < 0:
            raise ValidationException("unit_price", "cannot be negative")
        if line.discount < 0:
            raise ValidationException("discount", "cannot be negative")

        line_subtotal = line.unit_price * line.quantity
        line_after_discount = line_subtotal - line.discount
        line_tax = line_after_discount * line.tax_rate / Decimal("100")
        subtotal += line_after_discount
        tax_amount += line_tax
        discount_total += line.discount

    return InvoiceSummary(
        subtotal=subtotal,
        tax_amount=tax_amount,
        discount_total=discount_total,
        total=subtotal + tax_amount,
    )


# ============================================================
# Use Case: Create Invoice (with auto-journal posting)
# ============================================================
class CreateInvoiceUseCase:
    """إنشاء فاتورة + توليد قيد محاسبي تلقائي + ترحيله.

   Atomicity: كل العمليات (فاتورة + قيد + مخزون + رصيد العميل) تُنفّذ
    كمعاملة واحدة. لو فشلت أي خطوة، تُلغى كل التغييرات تلقائيًا.

    Args:
        invoice_repo: مستودع الفواتير
        customer_repo: مستودع العملاء
        supplier_repo: مستودع الموردين
        product_repo: مستودع المنتجات
        inventory_repo: مستودع المخزون
        journal_builder: بنّاء القيود التلقائي
        create_journal_uc: حالة استخدام إنشاء القيد
        post_journal_uc: حالة استخدام ترحيل القيد
    """

    def __init__(
        self,
        invoice_repo: IInvoiceRepository,
        customer_repo: ICustomerRepository,
        supplier_repo: ISupplierRepository,
        product_repo: IProductRepository,
        inventory_repo: IInventoryRepository,
        journal_builder: AutoJournalBuilder,
        create_journal_uc: CreateJournalEntryUseCase,
        post_journal_uc: PostJournalEntryUseCase,
    ) -> None:
        self._invoice_repo = invoice_repo
        self._customer_repo = customer_repo
        self._supplier_repo = supplier_repo
        self._product_repo = product_repo
        self._inventory_repo = inventory_repo
        self._journal_builder = journal_builder
        self._create_journal_uc = create_journal_uc
        self._post_journal_uc = post_journal_uc
        self._logger = None  # Will be set by logger factory if available

    def _log(self, level: str, message: str) -> None:
        """تسجيل رسالة في الـ logger (إن وُجد) أو stdout."""
        try:
            from loguru import logger
            getattr(logger, level)(message)
        except ImportError:
            pass

    async def execute(self, request: CreateInvoiceRequest, current_user) -> Invoice:
        # 1. Permission check
        required_perm = (
            Permission.INVOICE_CREATE
            if request.invoice_type in (InvoiceType.SALE, InvoiceType.PURCHASE)
            else Permission.INVOICE_CREATE
        )
        if not current_user.has_permission(required_perm):
            raise PermissionDeniedException("invoice.create")

        # 2. Validation
        if not request.lines:
            raise ValidationException("lines", "invoice must have at least one line")
        if request.invoice_type == InvoiceType.SALE and not request.customer_id:
            raise ValidationException("customer_id", "required for sale invoice")
        if request.invoice_type == InvoiceType.PURCHASE and not request.supplier_id:
            raise ValidationException("supplier_id", "required for purchase invoice")

        # 3. Verify party (customer/supplier) exists
        customer_code = ""
        supplier_code = ""
        if request.customer_id:
            customer = await self._customer_repo.get_by_id(request.customer_id)
            if customer is None:
                raise CustomerNotFoundException(str(request.customer_id))
            customer_code = customer.code
            # Credit limit check (for credit sales)
            if not request.is_cash and request.invoice_type == InvoiceType.SALE:
                totals = calculate_invoice_totals(request.lines)
                if not customer.is_within_credit_limit(totals.total):
                    raise CreditLimitExceededException(
                        customer.name,
                        float(customer.credit_limit),
                        float(customer.current_balance + totals.total),
                    )
        if request.supplier_id:
            supplier = await self._supplier_repo.get_by_id(request.supplier_id)
            if supplier is None:
                raise SupplierNotFoundException(str(request.supplier_id))
            supplier_code = supplier.code

        # 4. Verify products exist + check stock for sales
        validated_lines: list[tuple] = []  # (product, quantity, line_total)
        for line_dto in request.lines:
            product = await self._product_repo.get_by_id(line_dto.product_id)
            if product is None:
                raise ProductNotFoundException(str(line_dto.product_id))
            if not product.is_active:
                raise ValidationException(f"product {product.sku}", "is not active")

            # Stock check for sales
            if request.invoice_type == InvoiceType.SALE:
                current_stock = await self._inventory_repo.get_balance(product.id)
                if Decimal(str(current_stock)) < line_dto.quantity:
                    raise InsufficientStockException(
                        product.name,
                        float(line_dto.quantity),
                        current_stock,
                    )

            line_subtotal = line_dto.unit_price * line_dto.quantity - line_dto.discount
            line_tax = line_subtotal * line_dto.tax_rate / Decimal("100")
            line_total = line_subtotal + line_tax
            validated_lines.append((product, line_dto, line_total))

        # 5. Calculate totals
        totals = calculate_invoice_totals(request.lines)

        # 6. Generate invoice number
        invoice_no = await self._invoice_repo.next_invoice_no(request.invoice_type)

        # 7. Build invoice entity
        from domain.entities.invoice import Invoice, InvoiceItem
        invoice_id = uuid4()
        invoice = Invoice(
            id=invoice_id,
            invoice_no=invoice_no,
            invoice_type=request.invoice_type,
            customer_id=request.customer_id,
            supplier_id=request.supplier_id,
            issue_date=request.issue_date,
            due_date=request.due_date,
            subtotal=totals.subtotal,
            tax_amount=totals.tax_amount,
            discount=totals.discount_total,
            total=totals.total,
            status=InvoiceStatus.POSTED,  # posted immediately with journal
            notes=request.notes,
            created_by=current_user.id,
        )

        # Add line items
        for product, line_dto, line_total in validated_lines:
            item = InvoiceItem(
                invoice_id=invoice_id,
                product_id=product.id,
                quantity=line_dto.quantity,
                unit_price=line_dto.unit_price,
                tax_rate=line_dto.tax_rate,
                discount=line_dto.discount,
                line_total=line_total,
                description=line_dto.description or product.name,
            )
            invoice.items.append(item)

        # 8. Save invoice
        saved_invoice = await self._invoice_repo.save(invoice)

        # 9. Auto-generate journal entry
        if request.invoice_type == InvoiceType.SALE:
            journal_req = await self._journal_builder.build_sales_invoice_journal(
                invoice_no=invoice_no,
                customer_code=customer_code,
                subtotal=totals.subtotal,
                tax_amount=totals.tax_amount,
                total=totals.total,
                is_cash=request.is_cash,
            )
        elif request.invoice_type == InvoiceType.PURCHASE:
            journal_req = await self._journal_builder.build_purchase_invoice_journal(
                invoice_no=invoice_no,
                supplier_code=supplier_code,
                subtotal=totals.subtotal,
                tax_amount=totals.tax_amount,
                total=totals.total,
                is_cash=request.is_cash,
            )
        else:
            # Returns handled separately
            journal_req = None

        if journal_req is not None:
            journal_req.reference_id = invoice_id
            journal_entry = await self._create_journal_uc.execute(
                journal_req, created_by=current_user.id
            )
            # Post journal immediately
            posted_entry = await self._post_journal_uc.execute(
                journal_entry.id, posted_by=current_user.id
            )
            # Link journal to invoice
            saved_invoice.journal_entry_id = posted_entry.id
            await self._invoice_repo.save(saved_invoice)

        # 10. Update inventory (each line)
        # ⚠️ FIX: حساب balance_after بشكل صحيح بعد كل بند (وليس قبل)
        from domain.entities.product import InventoryEntry
        for product, line_dto, _ in validated_lines:
            current_balance = Decimal(
                str(await self._inventory_repo.get_balance(product.id))
            )
            if request.invoice_type == InvoiceType.SALE:
                new_balance = current_balance - line_dto.quantity
                entry = InventoryEntry(
                    product_id=product.id,
                    quantity_out=line_dto.quantity,
                    reference_type="invoice",
                    reference_id=invoice_id,
                    unit_cost=product.cost_price,
                    balance_after=new_balance,
                    created_by=current_user.id,
                )
            else:  # PURCHASE
                new_balance = current_balance + line_dto.quantity
                entry = InventoryEntry(
                    product_id=product.id,
                    quantity_in=line_dto.quantity,
                    reference_type="invoice",
                    reference_id=invoice_id,
                    unit_cost=line_dto.unit_price,
                    balance_after=new_balance,
                    created_by=current_user.id,
                )
            await self._inventory_repo.add_entry(entry)

        # 11. Update party balance (for credit transactions)
        if not request.is_cash:
            if request.invoice_type == InvoiceType.SALE and request.customer_id:
                customer.update_balance(totals.total)
                await self._customer_repo.save(customer)
            elif request.invoice_type == InvoiceType.PURCHASE and request.supplier_id:
                supplier.update_balance(totals.total)
                await self._supplier_repo.save(supplier)

        return saved_invoice


# ============================================================
# Use Case: Get Invoice
# ============================================================
class GetInvoiceUseCase:
    def __init__(self, invoice_repo: IInvoiceRepository) -> None:
        self._repo = invoice_repo

    async def execute(self, invoice_id: UUID, current_user) -> Invoice:
        if not current_user.has_permission(Permission.INVOICE_VIEW):
            raise PermissionDeniedException("invoice.view")
        invoice = await self._repo.get_by_id(invoice_id)
        if invoice is None:
            raise InvoiceNotFoundException(str(invoice_id))
        return invoice


# ============================================================
# Use Case: List Invoices
# ============================================================
class ListInvoicesUseCase:
    def __init__(self, invoice_repo: IInvoiceRepository) -> None:
        self._repo = invoice_repo

    async def execute(
        self, current_user, invoice_type: Optional[InvoiceType] = None,
        skip: int = 0, limit: int = 100,
    ) -> list[Invoice]:
        if not current_user.has_permission(Permission.INVOICE_VIEW):
            raise PermissionDeniedException("invoice.view")
        return await self._invoice_repo.list_all(
            invoice_type=invoice_type, skip=skip, limit=limit
        )


# ============================================================
# Use Case: Cancel Invoice (reverse journal)
# ============================================================
class CancelInvoiceUseCase:
    """إلغاء فاتورة: قيد عكسي + إعادة المخزون."""

    def __init__(
        self,
        invoice_repo: IInvoiceRepository,
        reverse_journal_uc,
    ) -> None:
        self._invoice_repo = invoice_repo
        self._reverse_journal_uc = reverse_journal_uc

    async def execute(self, invoice_id: UUID, current_user) -> Invoice:
        if not current_user.has_permission(Permission.INVOICE_DELETE):
            raise PermissionDeniedException("invoice.delete")

        invoice = await self._invoice_repo.get_by_id(invoice_id)
        if invoice is None:
            raise InvoiceNotFoundException(str(invoice_id))
        if invoice.status == InvoiceStatus.CANCELLED:
            raise InvoiceAlreadyPaidException(invoice.invoice_no)

        # Reverse the linked journal entry
        if invoice.journal_entry_id:
            await self._reverse_journal_uc.execute(
                invoice.journal_entry_id, reversed_by=current_user.id
            )

        invoice.status = InvoiceStatus.CANCELLED
        from datetime import datetime
        invoice.updated_at = datetime.now()
        return await self._invoice_repo.save(invoice)
