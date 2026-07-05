"""
Returns Use Cases - حالات استخدام المرتجعات

مرتجع بيع: استلام بضاعة من العميل، عكس قيد البيع.
مرتجع شراء: إرجاع بضاعة للمورد، عكس قيد الشراء.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from domain.entities.invoice import (
    Invoice, InvoiceItem, InvoiceStatus, InvoiceType,
)
from domain.entities.journal import JournalEntryReferenceType
from domain.exceptions.exceptions import (
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
from use_cases.invoices.invoice_use_cases import InvoiceLineDTO
from use_cases.journal.journal_use_cases import (
    AutoJournalBuilder, CreateJournalEntryUseCase, JournalLineDTO,
    PostJournalEntryUseCase, ReverseJournalEntryUseCase,
)
from use_cases.repositories.interfaces import (
    ICustomerRepository,
    IInventoryRepository,
    IInvoiceRepository,
    IProductRepository,
    ISupplierRepository,
)


@dataclass
class CreateReturnRequest:
    """طلب إنشاء مرتجع."""
    original_invoice_id: UUID
    lines: list[InvoiceLineDTO]  # المنتجات المُعادة وكمياتها
    reason: str = ""
    is_cash: bool = True  # استرداد نقدي أم شطب ذمة


class CreateReturnUseCase:
    """إنشاء مرتجع بيع/شراء.

    المرتجع:
    - ينشئ فاتورة من نوع SALE_RETURN أو PURCHASE_RETURN
    - يولّد قيدًا عكسيًا (يُعكس قيد الفاتورة الأصلية)
    - يُحدّث المخزون (استلام للمُرتجع بيع، إخراج للمُرتجع شراء)
    - يُحدّث رصيد العميل/المورد
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

    async def execute(self, request: CreateReturnRequest, current_user) -> Invoice:
        # 1. Permission check
        if not current_user.has_permission(Permission.INVOICE_CREATE):
            raise PermissionDeniedException("invoice.create")

        # 2. Load original invoice
        original = await self._invoice_repo.get_by_id(request.original_invoice_id)
        if original is None:
            raise InvoiceNotFoundException(str(request.original_invoice_id))
        if original.status == InvoiceStatus.CANCELLED:
            raise InvoiceAlreadyPaidException(original.invoice_no)
        if not original.is_posted():
            raise ValidationException(
                "original_invoice", "must be posted before returning"
            )

        # 3. Determine return type
        if original.invoice_type == InvoiceType.SALE:
            return_type = InvoiceType.SALE_RETURN
        elif original.invoice_type == InvoiceType.PURCHASE:
            return_type = InvoiceType.PURCHASE_RETURN
        else:
            raise ValidationException(
                "invoice_type", f"cannot return {original.invoice_type.value}"
            )

        # 4. Validate return quantities don't exceed original
        for line in request.lines:
            original_item = next(
                (it for it in original.items if it.product_id == line.product_id), None
            )
            if original_item is None:
                raise ValidationException(
                    "product", "not in original invoice"
                )
            if line.quantity > original_item.quantity:
                raise ValidationException(
                    "quantity",
                    f"return quantity {line.quantity} exceeds original {original_item.quantity}",
                )

        # 5. Calculate totals (mirror of original prices)
        from use_cases.invoices.invoice_use_cases import calculate_invoice_totals
        totals = calculate_invoice_totals(request.lines)

        # 6. Generate return invoice number
        return_no = await self._invoice_repo.next_invoice_no(return_type)

        # 7. Build return invoice
        return_invoice = Invoice(
            id=uuid4(),
            invoice_no=return_no,
            invoice_type=return_type,
            customer_id=original.customer_id,
            supplier_id=original.supplier_id,
            issue_date=datetime.now(),
            subtotal=totals.subtotal,
            tax_amount=totals.tax_amount,
            discount=totals.discount_total,
            total=totals.total,
            status=InvoiceStatus.POSTED,
            notes=f"مرتجع للفاتورة {original.invoice_no}. السبب: {request.reason}",
            created_by=current_user.id,
        )

        # Add items
        for line in request.lines:
            product = await self._product_repo.get_by_id(line.product_id)
            if product is None:
                raise ProductNotFoundException(str(line.product_id))

            line_subtotal = line.unit_price * line.quantity - line.discount
            line_tax = line_subtotal * line.tax_rate / Decimal("100")
            line_total = line_subtotal + line_tax

            item = InvoiceItem(
                invoice_id=return_invoice.id,
                product_id=product.id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=line.tax_rate,
                discount=line.discount,
                line_total=line_total,
                description=f"مرتجع: {product.name}",
            )
            return_invoice.items.append(item)

        # 8. Save return invoice
        saved_return = await self._invoice_repo.save(return_invoice)

        # 9. Generate REVERSE journal entry
        # For SALE_RETURN: reverse of sale
        #   from ح/ المبيعات (debit) + ض.ق.م (debit)
        #   to   ح/ الصندوق أو العملاء (credit)
        if return_type == InvoiceType.SALE_RETURN:
            # Reverse sale journal
            debit_account = "1101" if request.is_cash else "1103"
            journal_lines = [
                JournalLineDTO(account_code="4101", debit=float(totals.subtotal), description=f"مرتجع مبيعات {return_no}"),
                JournalLineDTO(account_code="2102", debit=float(totals.tax_amount), description=f"ضريبة مرتجع {return_no}"),
                JournalLineDTO(account_code=debit_account, credit=float(totals.total), description=f"استرداد مرتجع {return_no}"),
            ]
        else:  # PURCHASE_RETURN
            # Reverse purchase journal
            credit_account = "1101" if request.is_cash else "2101"
            journal_lines = [
                JournalLineDTO(account_code=credit_account, debit=float(totals.total), description=f"استرداد مرتجع {return_no}"),
                JournalLineDTO(account_code="5101", credit=float(totals.subtotal), description=f"مرتجع مشتريات {return_no}"),
                JournalLineDTO(account_code="1105", credit=float(totals.tax_amount), description=f"ضريبة مرتجع {return_no}"),
            ]

        from use_cases.journal.journal_use_cases import (
            CreateJournalEntryRequest,
        )
        journal_req = CreateJournalEntryRequest(
            description=f"قيد مرتجع {return_no} للفاتورة {original.invoice_no}",
            reference_type=JournalEntryReferenceType.RETURN,
            reference_id=saved_return.id,
            lines=journal_lines,
        )

        journal_entry = await self._create_journal_uc.execute(
            journal_req, created_by=current_user.id
        )
        posted_entry = await self._post_journal_uc.execute(
            journal_entry.id, posted_by=current_user.id
        )
        saved_return.journal_entry_id = posted_entry.id
        await self._invoice_repo.save(saved_return)

        # 10. Update inventory (reverse of original)
        from domain.entities.product import InventoryEntry
        for line in request.lines:
            product = await self._product_repo.get_by_id(line.product_id)
            current_balance = Decimal(
                str(await self._inventory_repo.get_balance(product.id))
            )

            if return_type == InvoiceType.SALE_RETURN:
                # Receiving product back from customer → IN
                entry = InventoryEntry(
                    product_id=product.id,
                    quantity_in=line.quantity,
                    reference_type="return",
                    reference_id=saved_return.id,
                    unit_cost=product.cost_price,
                    balance_after=current_balance + line.quantity,
                    created_by=current_user.id,
                )
            else:  # PURCHASE_RETURN
                # Sending product back to supplier → OUT
                if current_balance < line.quantity:
                    raise InsufficientStockException(
                        product.name,
                        float(line.quantity),
                        float(current_balance),
                    )
                entry = InventoryEntry(
                    product_id=product.id,
                    quantity_out=line.quantity,
                    reference_type="return",
                    reference_id=saved_return.id,
                    unit_cost=product.cost_price,
                    balance_after=current_balance - line.quantity,
                    created_by=current_user.id,
                )
            await self._inventory_repo.add_entry(entry)

        # 11. Update party balance (reverse)
        if not request.is_cash:
            if return_type == InvoiceType.SALE_RETURN and original.customer_id:
                customer = await self._customer_repo.get_by_id(original.customer_id)
                if customer:
                    customer.update_balance(-totals.total)  # reduce customer balance
                    await self._customer_repo.save(customer)
            elif return_type == InvoiceType.PURCHASE_RETURN and original.supplier_id:
                supplier = await self._supplier_repo.get_by_id(original.supplier_id)
                if supplier:
                    supplier.update_balance(-totals.total)
                    await self._supplier_repo.save(supplier)

        return saved_return
