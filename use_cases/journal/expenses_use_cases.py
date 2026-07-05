"""
Expenses & Revenues Use Cases - حالات استخدام المصروفات والإيرادات اليدوية

تسجيل مصروف عام (كهرباء، إيجار، رواتب) أو إيراد غير تشغيلي (فوائد بنكية).
كل عملية تُولّد قيدًا محاسبيًا تلقائيًا.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from domain.entities.journal import JournalEntryReferenceType
from domain.exceptions.exceptions import (
    AccountNotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from domain.value_objects.value_objects import Permission
from use_cases.journal.journal_use_cases import (
    AutoJournalBuilder, CreateJournalEntryUseCase, JournalLineDTO,
    PostJournalEntryUseCase, CreateJournalEntryRequest,
)
from use_cases.repositories.interfaces import IAccountRepository, IJournalEntryRepository


@dataclass
class RecordExpenseRequest:
    """طلب تسجيل مصروف."""
    description: str
    expense_account_code: str  # مثلًا: "5201" للرواتب
    amount: Decimal
    payment_account_code: str = "1101"  # الصندوق افتراضيًا
    is_cash: bool = True
    reference: str = ""  # رقم المستند


@dataclass
class RecordRevenueRequest:
    """طلب تسجيل إيراد."""
    description: str
    revenue_account_code: str  # مثلًا: "4201" للفوائد
    amount: Decimal
    receipt_account_code: str = "1101"  # الصندوق افتراضيًا
    is_cash: bool = True
    reference: str = ""


class RecordExpenseUseCase:
    """تسجيل مصروف عام.

    القيد:
        من ح/ المصروف (مدين)
        إلى ح/ الصندوق أو البنك (دائن)
    """

    def __init__(
        self,
        account_repo: IAccountRepository,
        journal_builder: AutoJournalBuilder,
        create_journal_uc: CreateJournalEntryUseCase,
        post_journal_uc: PostJournalEntryUseCase,
    ) -> None:
        self._account_repo = account_repo
        self._journal_builder = journal_builder
        self._create_journal_uc = create_journal_uc
        self._post_journal_uc = post_journal_uc

    async def execute(self, request: RecordExpenseRequest, current_user) -> str:
        """يُعيد رقم القيد المحاسبي."""
        if not current_user.has_permission(Permission.INVOICE_CREATE):
            raise PermissionDeniedException("expense.create")
        if not request.description:
            raise ValidationException("description", "is required")
        if request.amount <= 0:
            raise ValidationException("amount", "must be positive")

        # Verify accounts exist
        expense_account = await self._account_repo.get_by_code(request.expense_account_code)
        if expense_account is None:
            raise AccountNotFoundException(request.expense_account_code)
        payment_account = await self._account_repo.get_by_code(request.payment_account_code)
        if payment_account is None:
            raise AccountNotFoundException(request.payment_account_code)

        # Build journal request
        journal_req = CreateJournalEntryRequest(
            description=f"مصروف: {request.description}",
            reference_type=JournalEntryReferenceType.EXPENSE,
            lines=[
                JournalLineDTO(
                    account_code=request.expense_account_code,
                    debit=float(request.amount),
                    description=request.description,
                ),
                JournalLineDTO(
                    account_code=request.payment_account_code,
                    credit=float(request.amount),
                    description=f"سداد: {request.description}",
                ),
            ],
        )

        entry = await self._create_journal_uc.execute(journal_req, current_user.id)
        posted = await self._post_journal_uc.execute(entry.id, current_user.id)
        return posted.entry_no


class RecordRevenueUseCase:
    """تسجيل إيراد غير تشغيلي.

    القيد:
        من ح/ الصندوق أو البنك (مدين)
        إلى ح/ الإيراد (دائن)
    """

    def __init__(
        self,
        account_repo: IAccountRepository,
        journal_builder: AutoJournalBuilder,
        create_journal_uc: CreateJournalEntryUseCase,
        post_journal_uc: PostJournalEntryUseCase,
    ) -> None:
        self._account_repo = account_repo
        self._journal_builder = journal_builder
        self._create_journal_uc = create_journal_uc
        self._post_journal_uc = post_journal_uc

    async def execute(self, request: RecordRevenueRequest, current_user) -> str:
        if not current_user.has_permission(Permission.INVOICE_CREATE):
            raise PermissionDeniedException("revenue.create")
        if not request.description:
            raise ValidationException("description", "is required")
        if request.amount <= 0:
            raise ValidationException("amount", "must be positive")

        revenue_account = await self._account_repo.get_by_code(request.revenue_account_code)
        if revenue_account is None:
            raise AccountNotFoundException(request.revenue_account_code)
        receipt_account = await self._account_repo.get_by_code(request.receipt_account_code)
        if receipt_account is None:
            raise AccountNotFoundException(request.receipt_account_code)

        journal_req = CreateJournalEntryRequest(
            description=f"إيراد: {request.description}",
            reference_type=JournalEntryReferenceType.EXPENSE,  # generic for now
            lines=[
                JournalLineDTO(
                    account_code=request.receipt_account_code,
                    debit=float(request.amount),
                    description=f"استلام: {request.description}",
                ),
                JournalLineDTO(
                    account_code=request.revenue_account_code,
                    credit=float(request.amount),
                    description=request.description,
                ),
            ],
        )

        entry = await self._create_journal_uc.execute(journal_req, current_user.id)
        posted = await self._post_journal_uc.execute(entry.id, current_user.id)
        return posted.entry_no
