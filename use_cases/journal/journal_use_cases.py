"""
Journal Use Cases - حالات استخدام القيود المحاسبية

محرك القيد المزدوج: كل عملية تجارية (فاتورة، مصروف، تسوية)
تمر من هنا لتوليد القيود الصحيحة المتوازنة تلقائيًا.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from domain.entities.account import Account, AccountType
from domain.entities.journal import (
    JournalEntry,
    JournalEntryReferenceType,
    JournalEntryStatus,
    JournalLine,
)
from domain.exceptions.exceptions import (
    AccountNotFoundException,
    JournalEntryAlreadyPostedException,
    UnbalancedJournalEntryException,
    ValidationException,
)
from use_cases.repositories.interfaces import IAccountRepository, IJournalEntryRepository


# ============================================================
# DTOs
# ============================================================
@dataclass
class JournalLineDTO:
    """DTO لتمرير بيانات بند القيد."""

    account_code: str  # نستخدم الكود (لا ID) لتسهيل الاستخدام
    debit: float = 0.0
    credit: float = 0.0
    description: str = ""


@dataclass
class CreateJournalEntryRequest:
    """طلب إنشاء قيد محاسبي."""

    description: str
    lines: list[JournalLineDTO]
    reference_type: JournalEntryReferenceType = JournalEntryReferenceType.MANUAL
    reference_id: Optional[UUID] = None
    date: Optional[datetime] = None


# ============================================================
# Use Case: Create Journal Entry (Manual)
# ============================================================
class CreateJournalEntryUseCase:
    """حالة استخدام إنشاء قيد محاسبي يدوي.

    القواعد المُطبَّقة:
    - القيد يجب أن يكون متوازنًا (مدين = دائن)
    - كل الحسابات يجب أن تكون موجودة وفاعلة
    - لا يمكن تعديل قيد مرحّل
    """

    def __init__(
        self,
        journal_repo: IJournalEntryRepository,
        account_repo: IAccountRepository,
    ) -> None:
        self._journal_repo = journal_repo
        self._account_repo = account_repo

    async def execute(
        self, request: CreateJournalEntryRequest, created_by: UUID
    ) -> JournalEntry:
        # 1. التحقق من المدخلات
        if not request.description:
            raise ValidationException("description", "is required")
        if not request.lines or len(request.lines) < 2:
            raise ValidationException("lines", "must have at least 2 lines")

        # 2. توليد رقم القيد
        entry_no = await self._journal_repo.next_entry_no()

        # 3. إنشاء القيد
        entry = JournalEntry(
            entry_no=entry_no,
            date=request.date or datetime.now(),
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            description=request.description,
            status=JournalEntryStatus.DRAFT,
            created_by=created_by,
        )

        # 4. إضافة البنود (مع التحقق من وجود الحسابات)
        for line_dto in request.lines:
            account = await self._account_repo.get_by_code(line_dto.account_code)
            if account is None:
                raise AccountNotFoundException(line_dto.account_code)
            if not account.is_active:
                raise ValidationException(
                    f"account {line_dto.account_code}", "is not active"
                )

            entry.add_line(
                account_id=account.id,
                debit=Decimal(str(line_dto.debit)),
                credit=Decimal(str(line_dto.credit)),
                description=line_dto.description,
            )

        # 5. التحقق من التوازن
        entry.assert_balanced()

        # 6. الحفظ
        return await self._journal_repo.save(entry)


# ============================================================
# Use Case: Post Journal Entry
# ============================================================
class PostJournalEntryUseCase:
    """حالة استخدام ترحيل القيد (قفله + توليد الأثر)."""

    def __init__(self, journal_repo: IJournalEntryRepository) -> None:
        self._journal_repo = journal_repo

    async def execute(self, entry_id: UUID, posted_by: UUID) -> JournalEntry:
        entry = await self._journal_repo.get_by_id(entry_id)
        if entry is None:
            raise JournalEntryAlreadyPostedException(str(entry_id))

        entry.post(posted_by=posted_by)
        return await self._journal_repo.save(entry)


# ============================================================
# Use Case: Reverse Journal Entry
# ============================================================
class ReverseJournalEntryUseCase:
    """حالة استخدام قلب قيد مرحّل (بقيد عكسي)."""

    def __init__(self, journal_repo: IJournalEntryRepository) -> None:
        self._journal_repo = journal_repo

    async def execute(self, entry_id: UUID, reversed_by: UUID) -> JournalEntry:
        original = await self._journal_repo.get_by_id(entry_id)
        if original is None:
            raise JournalEntryAlreadyPostedException(str(entry_id))

        reversed_entry = original.reverse(reversed_by=reversed_by)
        # حفظ القيد الأصلي (لتغيير حالته إلى REVERSED)
        await self._journal_repo.save(original)
        # حفظ القيد العكسي
        return await self._journal_repo.save(reversed_entry)


# ============================================================
# Use Case: Get Trial Balance (ميزان المراجعة)
# ============================================================
@dataclass
class TrialBalanceLine:
    account_code: str
    account_name: str
    account_type: str
    debit: float
    credit: float


@dataclass
class TrialBalanceResult:
    lines: list[TrialBalanceLine]
    total_debit: float
    total_credit: float
    is_balanced: bool
    difference: float


class GetTrialBalanceUseCase:
    """حالة استخدام إصدار ميزان المراجعة."""

    def __init__(
        self,
        account_repo: IAccountRepository,
        journal_repo: IJournalEntryRepository,
    ) -> None:
        self._account_repo = account_repo
        self._journal_repo = journal_repo

    async def execute(self, as_of_date: Optional[datetime] = None) -> TrialBalanceResult:
        as_of = as_of_date or datetime.now()
        # TODO: implement trial balance computation from journal entries
        # For now, return empty (will be implemented in next iteration)
        return TrialBalanceResult(
            lines=[],
            total_debit=0.0,
            total_credit=0.0,
            is_balanced=True,
            difference=0.0,
        )


# ============================================================
# Auto-Journal Builder (helper used by invoice use cases)
# ============================================================
class AutoJournalBuilder:
    """بنّاء القيود التلقائي.

    Helper يستخدمه الـ use cases للفواتير والمصروفات
    لتوليد القيود الصحيحة تلقائيًا وفق القواعد المحاسبية.
    """

    def __init__(self, account_repo: IAccountRepository) -> None:
        self._account_repo = account_repo

    async def build_sales_invoice_journal(
        self,
        invoice_no: str,
        customer_code: str,
        subtotal: Decimal,
        tax_amount: Decimal,
        total: Decimal,
        is_cash: bool = False,
    ) -> CreateJournalEntryRequest:
        """توليد قيد فاتورة بيع.

        إذا نقدي:
            من ح/ الصندوق (total)
            إلى ح/ المبيعات (subtotal)
            إلى ح/ ض.ق.م المستحقة (tax)

        إذا آجل:
            من ح/ العملاء (total)
            إلى ح/ المبيعات (subtotal)
            إلى ح/ ض.ق.م المستحقة (tax)
        """
        debit_account = "1101" if is_cash else "1103"  # الصندوق أو العملاء
        return CreateJournalEntryRequest(
            description=f"فاتورة بيع {invoice_no} - عميل {customer_code}",
            reference_type=JournalEntryReferenceType.INVOICE,
            lines=[
                JournalLineDTO(
                    account_code=debit_account,
                    debit=float(total),
                    description=f"فاتورة بيع {invoice_no}",
                ),
                JournalLineDTO(
                    account_code="4101",  # المبيعات
                    credit=float(subtotal),
                    description=f"إيراد مبيعات {invoice_no}",
                ),
                JournalLineDTO(
                    account_code="2102",  # ض.ق.م المستحقة
                    credit=float(tax_amount),
                    description=f"ضريبة قيمة مضافة {invoice_no}",
                ),
            ],
        )

    async def build_purchase_invoice_journal(
        self,
        invoice_no: str,
        supplier_code: str,
        subtotal: Decimal,
        tax_amount: Decimal,
        total: Decimal,
        is_cash: bool = False,
    ) -> CreateJournalEntryRequest:
        """توليد قيد فاتورة شراء.

        من ح/ المشتريات (subtotal)
        من ح/ ض.ق.م المدخلات (tax)
        إلى ح/ الصندوق (total) أو الموردين (total)
        """
        credit_account = "1101" if is_cash else "2101"  # الصندوق أو الموردين
        return CreateJournalEntryRequest(
            description=f"فاتورة شراء {invoice_no} - مورد {supplier_code}",
            reference_type=JournalEntryReferenceType.INVOICE,
            lines=[
                JournalLineDTO(
                    account_code="5101",  # المشتريات
                    debit=float(subtotal),
                    description=f"مشتريات {invoice_no}",
                ),
                JournalLineDTO(
                    account_code="1105",  # ض.ق.م المدخلات (أصل)
                    debit=float(tax_amount),
                    description=f"ضريبة مدخلات {invoice_no}",
                ),
                JournalLineDTO(
                    account_code=credit_account,
                    credit=float(total),
                    description=f"سداد {invoice_no}",
                ),
            ],
        )

    async def build_expense_journal(
        self,
        expense_description: str,
        account_code: str,
        amount: Decimal,
        is_cash: bool = True,
    ) -> CreateJournalEntryRequest:
        """توليد قيد مصروف.

        من ح/ المصروف (account_code)
        إلى ح/ الصندوق أو البنك
        """
        credit_account = "1101" if is_cash else "1102"  # الصندوق أو البنك
        return CreateJournalEntryRequest(
            description=f"مصروف: {expense_description}",
            reference_type=JournalEntryReferenceType.EXPENSE,
            lines=[
                JournalLineDTO(
                    account_code=account_code,
                    debit=float(amount),
                    description=expense_description,
                ),
                JournalLineDTO(
                    account_code=credit_account,
                    credit=float(amount),
                    description=f"سداد مصروف: {expense_description}",
                ),
            ],
        )
