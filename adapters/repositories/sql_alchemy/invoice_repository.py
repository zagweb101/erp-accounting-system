"""
SQLAlchemy Invoice Repository Implementation
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_

from domain.entities.invoice import Invoice, InvoiceItem, InvoiceStatus, InvoiceType
from infrastructure.db.models.invoice_model import InvoiceItemModel, InvoiceModel
from infrastructure.db.session import session_scope
from use_cases.repositories.interfaces import IInvoiceRepository


# Prefix mapping for invoice numbers
INVOICE_PREFIXES = {
    InvoiceType.SALE: "INV-S",          # INV-S-2026-000001
    InvoiceType.PURCHASE: "INV-P",      # INV-P-2026-000001
    InvoiceType.SALE_RETURN: "RET-S",   # RET-S-2026-000001
    InvoiceType.PURCHASE_RETURN: "RET-P",  # RET-P-2026-000001
}


class SqlAlchemyInvoiceRepository(IInvoiceRepository):
    def _to_entity(self, m: InvoiceModel) -> Invoice:
        """ To Entity."""
        invoice = Invoice(
            id=UUID(m.id),
            invoice_no=m.invoice_no,
            invoice_type=InvoiceType(m.invoice_type),
            customer_id=UUID(m.customer_id) if m.customer_id else None,
            supplier_id=UUID(m.supplier_id) if m.supplier_id else None,
            issue_date=m.issue_date,
            due_date=m.due_date,
            subtotal=Decimal(str(m.subtotal)),
            tax_amount=Decimal(str(m.tax_amount)),
            discount=Decimal(str(m.discount)),
            total=Decimal(str(m.total)),
            status=InvoiceStatus(m.status),
            notes=m.notes,
            journal_entry_id=UUID(m.journal_entry_id) if m.journal_entry_id else None,
            created_by=UUID(m.created_by),
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        if m.items:
            for im in m.items:
                item = InvoiceItem(
                    id=UUID(im.id),
                    invoice_id=invoice.id,
                    product_id=UUID(im.product_id),
                    quantity=Decimal(str(im.quantity)),
                    unit_price=Decimal(str(im.unit_price)),
                    tax_rate=Decimal(str(im.tax_rate)),
                    discount=Decimal(str(im.discount)),
                    line_total=Decimal(str(im.line_total)),
                    description=im.description,
                )
                invoice.items.append(item)
        return invoice

    async def get_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        with session_scope() as s:
            m = s.execute(
                select(InvoiceModel).where(InvoiceModel.id == str(invoice_id))
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def get_by_no(self, invoice_no: str) -> Optional[Invoice]:
        with session_scope() as s:
            m = s.execute(
                select(InvoiceModel).where(InvoiceModel.invoice_no == invoice_no)
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def save(self, invoice: Invoice) -> Invoice:
        with session_scope() as s:
            existing = s.execute(
                select(InvoiceModel).where(InvoiceModel.id == str(invoice.id))
            ).scalar_one_or_none()

            if existing is None:
                m = InvoiceModel(
                    id=str(invoice.id),
                    invoice_no=invoice.invoice_no,
                    invoice_type=invoice.invoice_type.value,
                    customer_id=str(invoice.customer_id) if invoice.customer_id else None,
                    supplier_id=str(invoice.supplier_id) if invoice.supplier_id else None,
                    issue_date=invoice.issue_date,
                    due_date=invoice.due_date,
                    subtotal=invoice.subtotal,
                    tax_amount=invoice.tax_amount,
                    discount=invoice.discount,
                    total=invoice.total,
                    status=invoice.status.value,
                    notes=invoice.notes,
                    journal_entry_id=str(invoice.journal_entry_id) if invoice.journal_entry_id else None,
                    created_by=str(invoice.created_by),
                )
            else:
                m = existing
                m.invoice_no = invoice.invoice_no
                m.invoice_type = invoice.invoice_type.value
                m.customer_id = str(invoice.customer_id) if invoice.customer_id else None
                m.supplier_id = str(invoice.supplier_id) if invoice.supplier_id else None
                m.issue_date = invoice.issue_date
                m.due_date = invoice.due_date
                m.subtotal = invoice.subtotal
                m.tax_amount = invoice.tax_amount
                m.discount = invoice.discount
                m.total = invoice.total
                m.status = invoice.status.value
                m.notes = invoice.notes
                m.journal_entry_id = str(invoice.journal_entry_id) if invoice.journal_entry_id else None

            # Sync items (delete + add)
            if existing is not None:
                for old_item in list(m.items):
                    s.delete(old_item)
                m.items = []

            for item in invoice.items:
                im = InvoiceItemModel(
                    id=str(item.id),
                    invoice_id=m.id,
                    product_id=str(item.product_id),
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    tax_rate=item.tax_rate,
                    discount=item.discount,
                    line_total=item.line_total,
                    description=item.description,
                )
                m.items.append(im)

            s.add(m)
            s.flush()
            s.refresh(m)
            return self._to_entity(m)

    async def list_all(
        self, invoice_type: Optional[InvoiceType] = None,
        skip: int = 0, limit: int = 100,
    ) -> list[Invoice]:
        with session_scope() as s:
            stmt = select(InvoiceModel).order_by(InvoiceModel.issue_date.desc())
            if invoice_type:
                stmt = stmt.where(InvoiceModel.invoice_type == invoice_type.value)
            stmt = stmt.offset(skip).limit(limit)
            models = s.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]

    async def list_by_customer(
        self, customer_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Invoice]:
        with session_scope() as s:
            stmt = (
                select(InvoiceModel)
                .where(InvoiceModel.customer_id == str(customer_id))
                .order_by(InvoiceModel.issue_date.desc())
                .offset(skip)
                .limit(limit)
            )
            models = s.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]

    async def list_by_supplier(
        self, supplier_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Invoice]:
        with session_scope() as s:
            stmt = (
                select(InvoiceModel)
                .where(InvoiceModel.supplier_id == str(supplier_id))
                .order_by(InvoiceModel.issue_date.desc())
                .offset(skip)
                .limit(limit)
            )
            models = s.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]


    async def _save_in_session(self, invoice: Invoice, session) -> Invoice:
        """حفظ الفاتورة في session موجودة (للـ UnitOfWork)."""
        existing = session.execute(
            select(InvoiceModel).where(InvoiceModel.id == str(invoice.id))
        ).scalar_one_or_none()

        if existing is None:
            m = InvoiceModel(
                id=str(invoice.id),
                invoice_no=invoice.invoice_no,
                invoice_type=invoice.invoice_type.value,
                customer_id=str(invoice.customer_id) if invoice.customer_id else None,
                supplier_id=str(invoice.supplier_id) if invoice.supplier_id else None,
                issue_date=invoice.issue_date,
                due_date=invoice.due_date,
                subtotal=invoice.subtotal,
                tax_amount=invoice.tax_amount,
                discount=invoice.discount,
                total=invoice.total,
                status=invoice.status.value,
                notes=invoice.notes,
                journal_entry_id=str(invoice.journal_entry_id) if invoice.journal_entry_id else None,
                created_by=str(invoice.created_by),
            )
        else:
            m = existing
            m.invoice_no = invoice.invoice_no
            m.invoice_type = invoice.invoice_type.value
            m.customer_id = str(invoice.customer_id) if invoice.customer_id else None
            m.supplier_id = str(invoice.supplier_id) if invoice.supplier_id else None
            m.issue_date = invoice.issue_date
            m.due_date = invoice.due_date
            m.subtotal = invoice.subtotal
            m.tax_amount = invoice.tax_amount
            m.discount = invoice.discount
            m.total = invoice.total
            m.status = invoice.status.value
            m.notes = invoice.notes
            m.journal_entry_id = str(invoice.journal_entry_id) if invoice.journal_entry_id else None

        if existing is not None:
            for old_item in list(m.items):
                session.delete(old_item)
            m.items = []

        for item in invoice.items:
            im = InvoiceItemModel(
                id=str(item.id),
                invoice_id=m.id,
                product_id=str(item.product_id),
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate,
                discount=item.discount,
                line_total=item.line_total,
                description=item.description,
            )
            m.items.append(im)

        session.add(m)
        session.flush()
        session.refresh(m)
        return self._to_entity(m)

    async def _add_inventory_in_session(self, entry, session) -> None:
        """إضافة حركة مخزون في session موجودة."""
        from infrastructure.db.models.product_model import InventoryEntryModel
        m = InventoryEntryModel(
            id=str(entry.id),
            product_id=str(entry.product_id),
            quantity_in=entry.quantity_in,
            quantity_out=entry.quantity_out,
            reference_type=entry.reference_type,
            reference_id=str(entry.reference_id) if entry.reference_id else None,
            unit_cost=entry.unit_cost,
            balance_after=entry.balance_after,
            created_by=str(entry.created_by) if entry.created_by else None,
        )
        session.add(m)
        session.flush()

    async def next_invoice_no(self, invoice_type: InvoiceType) -> str:
        """توليد رقم فاتورة تسلسلي: INV-S-2026-000001"""
        prefix = INVOICE_PREFIXES.get(invoice_type, "INV")
        year = datetime.now().year
        full_prefix = f"{prefix}-{year}-"
        with session_scope() as s:
            stmt = select(func.count(InvoiceModel.id)).where(
                InvoiceModel.invoice_no.like(f"{full_prefix}%")
            )
            count = s.execute(stmt).scalar() or 0
            return f"{full_prefix}{count + 1:06d}"
