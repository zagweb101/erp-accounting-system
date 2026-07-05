"""
SQLAlchemy Report Repository Implementation

يُنفّذ كل الاستعلامات المعقدة (GROUP BY, JOIN, SUM) هنا بدلًا من use_cases.
هذا يحل مخالفة Clean Architecture في reports_use_cases.py.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_

from domain.entities.journal import JournalEntryStatus
from domain.value_objects.value_objects import AccountType
from infrastructure.db.models.account_model import AccountModel
from infrastructure.db.models.journal_model import JournalEntryModel, JournalLineModel
from infrastructure.db.session import session_scope


class ReportRow:
    """صف واحد في تقرير (generic)."""

    def __init__(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class SqlAlchemyReportRepository:
    """مستودع التقارير - يُنفّذ استعلامات SQL المعقدة.

    كل الدوال تُعيد بيانات خام (dicts أو dataclasses)،
    الـ use cases تُنسّقها في تقارير نهائية.
    """

    def get_account_balances(
        self, as_of_date: datetime
    ) -> list[dict]:
        """أرصدة كل الحسابات حتى تاريخ معين.

        Returns: list of {
            account_id, code, name, account_type,
            total_debit, total_credit
        }
        """
        with session_scope() as s:
            stmt = (
                select(
                    AccountModel.id.label("aid"),
                    AccountModel.code.label("code"),
                    AccountModel.name.label("name"),
                    AccountModel.account_type.label("type"),
                    func.coalesce(func.sum(JournalLineModel.debit), 0).label("total_debit"),
                    func.coalesce(func.sum(JournalLineModel.credit), 0).label("total_credit"),
                )
                .outerjoin(JournalLineModel, JournalLineModel.account_id == AccountModel.id)
                .outerjoin(
                    JournalEntryModel,
                    and_(
                        JournalLineModel.entry_id == JournalEntryModel.id,
                        JournalEntryModel.status == JournalEntryStatus.POSTED.value,
                        JournalEntryModel.date <= as_of_date,
                    ),
                )
                .where(AccountModel.is_active == True)  # noqa: E712
                .where(AccountModel.is_posting_account == True)  # noqa: E712
                .group_by(
                    AccountModel.id, AccountModel.code, AccountModel.name, AccountModel.account_type
                )
                .order_by(AccountModel.code)
            )
            result = s.execute(stmt).all()
            return [
                {
                    "account_id": r.aid,
                    "code": r.code,
                    "name": r.name,
                    "account_type": r.type,
                    "total_debit": Decimal(str(r.total_debit)),
                    "total_credit": Decimal(str(r.total_credit)),
                }
                for r in result
            ]

    def get_income_statement_data(
        self, start_date: datetime, end_date: datetime
    ) -> list[dict]:
        """بيانات قائمة الدخل (الإيرادات والمصروفات خلال فترة).

        Returns: list of {code, name, account_type, debit, credit}
        """
        with session_scope() as s:
            stmt = (
                select(
                    AccountModel.code,
                    AccountModel.name,
                    AccountModel.account_type,
                    func.coalesce(func.sum(JournalLineModel.debit), 0).label("debit"),
                    func.coalesce(func.sum(JournalLineModel.credit), 0).label("credit"),
                )
                .join(JournalLineModel, JournalLineModel.account_id == AccountModel.id)
                .join(
                    JournalEntryModel,
                    and_(
                        JournalLineModel.entry_id == JournalEntryModel.id,
                        JournalEntryModel.status == JournalEntryStatus.POSTED.value,
                        JournalEntryModel.date >= start_date,
                        JournalEntryModel.date <= end_date,
                    ),
                )
                .where(AccountModel.is_active == True)  # noqa: E712
                .where(AccountModel.is_posting_account == True)  # noqa: E712
                .where(AccountModel.account_type.in_(
                    [AccountType.REVENUE.value, AccountType.EXPENSE.value]
                ))
                .group_by(AccountModel.code, AccountModel.name, AccountModel.account_type)
                .order_by(AccountModel.code)
            )
            result = s.execute(stmt).all()
            return [
                {
                    "code": r.code,
                    "name": r.name,
                    "account_type": r.account_type,
                    "debit": Decimal(str(r.debit)),
                    "credit": Decimal(str(r.credit)),
                }
                for r in result
            ]

    def get_account_statement_lines(
        self,
        account_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> tuple[Decimal, list[dict]]:
        """كشف حساب: رصيد افتتاحي + حركات الفترة.

        Returns: (opening_balance, list of {date, entry_no, description, debit, credit})
        """
        with session_scope() as s:
            # Opening balance (before start_date)
            opening_stmt = (
                select(
                    func.coalesce(func.sum(JournalLineModel.debit), 0).label("debit"),
                    func.coalesce(func.sum(JournalLineModel.credit), 0).label("credit"),
                )
                .join(
                    JournalEntryModel,
                    and_(
                        JournalLineModel.entry_id == JournalEntryModel.id,
                        JournalEntryModel.status == JournalEntryStatus.POSTED.value,
                        JournalEntryModel.date < start_date,
                    ),
                )
                .where(JournalLineModel.account_id == str(account_id))
            )
            opening = s.execute(opening_stmt).one()
            opening_debit = Decimal(str(opening.debit))
            opening_credit = Decimal(str(opening.credit))

            # Get account type for normal balance
            acc = s.execute(
                select(AccountModel).where(AccountModel.id == str(account_id))
            ).scalar_one_or_none()
            if acc is None:
                from domain.exceptions.exceptions import AccountNotFoundException
                raise AccountNotFoundException(str(account_id))

            account_type = AccountType(acc.account_type)
            if account_type.normal_balance == "DEBIT":
                opening_balance = opening_debit - opening_credit
            else:
                opening_balance = opening_credit - opening_debit

            # Lines in date range
            lines_stmt = (
                select(
                    JournalEntryModel.date,
                    JournalEntryModel.entry_no,
                    JournalLineModel.description,
                    JournalLineModel.debit,
                    JournalLineModel.credit,
                )
                .join(
                    JournalEntryModel,
                    and_(
                        JournalLineModel.entry_id == JournalEntryModel.id,
                        JournalEntryModel.status == JournalEntryStatus.POSTED.value,
                        JournalEntryModel.date >= start_date,
                        JournalEntryModel.date <= end_date,
                    ),
                )
                .where(JournalLineModel.account_id == str(account_id))
                .order_by(JournalEntryModel.date, JournalEntryModel.entry_no)
            )
            line_results = s.execute(lines_stmt).all()
            lines = [
                {
                    "date": r.date,
                    "entry_no": r.entry_no,
                    "description": r.description or "",
                    "debit": Decimal(str(r.debit)),
                    "credit": Decimal(str(r.credit)),
                }
                for r in line_results
            ]

            return opening_balance, lines, account_type
