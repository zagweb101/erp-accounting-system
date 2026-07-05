"""
Reports Use Cases - حالات استخدام التقارير المالية

- ميزان المراجعة (Trial Balance)
- قائمة المركز المالي (Balance Sheet)
- قائمة الدخل (Income Statement)
- كشف حساب (Account Statement)

✅ Clean Architecture compliant:
   لا تستورد من infrastructure مباشرة.
   تستخدم ReportRepository (مُحقَن عبر constructor) للوصول للبيانات.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from domain.entities.journal import JournalEntryStatus
from domain.value_objects.value_objects import AccountType


# ============================================================
# DTOs (Data Transfer Objects)
# ============================================================
@dataclass
class TrialBalanceLine:
    """بند في ميزان المراجعة."""
    account_code: str
    account_name: str
    account_type: str
    debit: Decimal
    credit: Decimal


@dataclass
class TrialBalanceReport:
    """تقرير ميزان المراجعة."""
    as_of_date: datetime
    lines: list[TrialBalanceLine]
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool
    difference: Decimal


@dataclass
class BalanceSheetLine:
    """بند في قائمة المركز المالي."""
    account_code: str
    account_name: str
    amount: Decimal


@dataclass
class BalanceSheetReport:
    """تقرير قائمة المركز المالي."""
    as_of_date: datetime
    assets: list[BalanceSheetLine]
    liabilities: list[BalanceSheetLine]
    equity: list[BalanceSheetLine]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    is_balanced: bool


@dataclass
class IncomeStatementLine:
    """بند في قائمة الدخل."""
    account_code: str
    account_name: str
    amount: Decimal


@dataclass
class IncomeStatementReport:
    """تقرير قائمة الدخل."""
    start_date: datetime
    end_date: datetime
    revenues: list[IncomeStatementLine]
    expenses: list[IncomeStatementLine]
    total_revenue: Decimal
    total_expense: Decimal
    net_income: Decimal
    is_profit: bool


@dataclass
class AccountStatementLine:
    """بند في كشف حساب."""
    date: datetime
    entry_no: str
    description: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


@dataclass
class AccountStatementReport:
    """تقرير كشف حساب."""
    account_code: str
    account_name: str
    start_date: datetime
    end_date: datetime
    opening_balance: Decimal
    lines: list[AccountStatementLine]
    closing_balance: Decimal


# ============================================================
# Use Case: Generate Trial Balance
# ============================================================
class GenerateTrialBalanceUseCase:
    """حالة استخدام إصدار ميزان المراجعة.

    Args:
        report_repository: مستودع التقارير (dependency injection).
            إن لم يُمرَّر، يُنشئ افتراضيًا من adapters.
    """

    def __init__(self, report_repository=None) -> None:
        self._report_repo = report_repository

    def _get_repo(self):
        """الحصول على الـ repository (lazy init إن لم يُمرَّر)."""
        if self._report_repo is not None:
            return self._report_repo
        # Lazy import لتجنب الـ circular imports
        from adapters.repositories.sql_alchemy.report_repository import SqlAlchemyReportRepository
        self._report_repo = SqlAlchemyReportRepository()
        return self._report_repo

    async def execute(
        self, as_of_date: Optional[datetime] = None, current_user=None
    ) -> TrialBalanceReport:
        """تنفيذ إصدار ميزان المراجعة.

        Args:
            as_of_date: التاريخ المرجعي (افتراضي: الآن).
            current_user: المستخدم الحالي للتحقق من الصلاحية.

        Returns:
            TrialBalanceReport مع الأرصدة والإجماليات.

        Raises:
            PermissionDeniedException: لو لم يكن لديك صلاحية report.view.
        """
        from domain.value_objects.value_objects import Permission
        if current_user and not current_user.has_permission(Permission.REPORT_VIEW):
            from domain.exceptions.exceptions import PermissionDeniedException
            raise PermissionDeniedException("report.view")

        as_of = as_of_date or datetime.now()
        repo = self._get_repo()
        balances_raw = repo.get_account_balances(as_of)

        lines: list[TrialBalanceLine] = []
        total_debit = Decimal("0")
        total_credit = Decimal("0")

        for r in balances_raw:
            code = r["code"]
            name = r["name"]
            acc_type = r["account_type"]
            dr = r["total_debit"]
            cr = r["total_credit"]

            # Net balance based on account type normal balance
            account_type = AccountType(acc_type)
            if account_type.normal_balance == "DEBIT":
                net = dr - cr
                if net >= 0:
                    line_debit = net
                    line_credit = Decimal("0")
                else:
                    line_debit = Decimal("0")
                    line_credit = abs(net)
            else:  # CREDIT normal
                net = cr - dr
                if net >= 0:
                    line_debit = Decimal("0")
                    line_credit = net
                else:
                    line_debit = abs(net)
                    line_credit = Decimal("0")

            # Skip zero-balance accounts
            if line_debit == 0 and line_credit == 0:
                continue

            lines.append(TrialBalanceLine(
                account_code=code,
                account_name=name,
                account_type=acc_type,
                debit=line_debit,
                credit=line_credit,
            ))
            total_debit += line_debit
            total_credit += line_credit

        return TrialBalanceReport(
            as_of_date=as_of,
            lines=lines,
            total_debit=total_debit,
            total_credit=total_credit,
            is_balanced=(total_debit == total_credit),
            difference=total_debit - total_credit,
        )


# ============================================================
# Use Case: Generate Balance Sheet
# ============================================================
class GenerateBalanceSheetUseCase:
    """حالة استخدام إصدار قائمة المركز المالي.

    Args:
        report_repository: مستودع التقارير.
    """

    def __init__(self, report_repository=None) -> None:
        self._report_repo = report_repository

    def _get_repo(self):
        """الحصول على الـ repository."""
        if self._report_repo is not None:
            return self._report_repo
        from adapters.repositories.sql_alchemy.report_repository import SqlAlchemyReportRepository
        self._report_repo = SqlAlchemyReportRepository()
        return self._report_repo

    async def execute(
        self, as_of_date: Optional[datetime] = None, current_user=None
    ) -> BalanceSheetReport:
        """تنفيذ إصدار قائمة المركز المالي.

        Args:
            as_of_date: التاريخ المرجعي.
            current_user: المستخدم الحالي.

        Returns:
            BalanceSheetReport مع الأصول والخصوم وحقوق الملكية.
        """
        from domain.value_objects.value_objects import Permission
        if current_user and not current_user.has_permission(Permission.REPORT_VIEW):
            from domain.exceptions.exceptions import PermissionDeniedException
            raise PermissionDeniedException("report.view")

        as_of = as_of_date or datetime.now()
        repo = self._get_repo()
        balances_raw = repo.get_account_balances(as_of)

        assets: list[BalanceSheetLine] = []
        liabilities: list[BalanceSheetLine] = []
        equity: list[BalanceSheetLine] = []

        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        total_equity = Decimal("0")

        for r in balances_raw:
            account_type = AccountType(r["account_type"])
            dr = r["total_debit"]
            cr = r["total_credit"]

            if account_type == AccountType.ASSET:
                amount = dr - cr
                if amount != 0:
                    assets.append(BalanceSheetLine(r["code"], r["name"], amount))
                    total_assets += amount
            elif account_type == AccountType.LIABILITY:
                amount = cr - dr
                if amount != 0:
                    liabilities.append(BalanceSheetLine(r["code"], r["name"], amount))
                    total_liabilities += amount
            elif account_type == AccountType.EQUITY:
                amount = cr - dr
                if amount != 0:
                    equity.append(BalanceSheetLine(r["code"], r["name"], amount))
                    total_equity += amount

        return BalanceSheetReport(
            as_of_date=as_of,
            assets=assets,
            liabilities=liabilities,
            equity=equity,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
            is_balanced=(total_assets == total_liabilities + total_equity),
        )


# ============================================================
# Use Case: Generate Income Statement
# ============================================================
class GenerateIncomeStatementUseCase:
    """حالة استخدام إصدار قائمة الدخل.

    Args:
        report_repository: مستودع التقارير.
    """

    def __init__(self, report_repository=None) -> None:
        self._report_repo = report_repository

    def _get_repo(self):
        """الحصول على الـ repository."""
        if self._report_repo is not None:
            return self._report_repo
        from adapters.repositories.sql_alchemy.report_repository import SqlAlchemyReportRepository
        self._report_repo = SqlAlchemyReportRepository()
        return self._report_repo

    async def execute(
        self,
        start_date: datetime,
        end_date: datetime,
        current_user=None,
    ) -> IncomeStatementReport:
        """تنفيذ إصدار قائمة الدخل.

        Args:
            start_date: بداية الفترة.
            end_date: نهاية الفترة.
            current_user: المستخدم الحالي.

        Returns:
            IncomeStatementReport مع الإيرادات والمصروفات وصافي الدخل.
        """
        from domain.value_objects.value_objects import Permission
        if current_user and not current_user.has_permission(Permission.REPORT_VIEW):
            from domain.exceptions.exceptions import PermissionDeniedException
            raise PermissionDeniedException("report.view")

        repo = self._get_repo()
        raw_data = repo.get_income_statement_data(start_date, end_date)

        revenues: list[IncomeStatementLine] = []
        expenses: list[IncomeStatementLine] = []
        total_revenue = Decimal("0")
        total_expense = Decimal("0")

        for r in raw_data:
            amount = Decimal(str(r["credit"] - r["debit"] if r["account_type"] == AccountType.REVENUE.value
                                 else r["debit"] - r["credit"]))
            line = IncomeStatementLine(r["code"], r["name"], amount)
            if r["account_type"] == AccountType.REVENUE.value:
                revenues.append(line)
                total_revenue += amount
            else:
                expenses.append(line)
                total_expense += amount

        net_income = total_revenue - total_expense

        return IncomeStatementReport(
            start_date=start_date,
            end_date=end_date,
            revenues=revenues,
            expenses=expenses,
            total_revenue=total_revenue,
            total_expense=total_expense,
            net_income=net_income,
            is_profit=(net_income >= 0),
        )


# ============================================================
# Use Case: Generate Account Statement
# ============================================================
class GenerateAccountStatementUseCase:
    """حالة استخدام إصدار كشف حساب.

    Args:
        report_repository: مستودع التقارير.
        account_repository: مستودع الحسابات (للتحقق من وجود الحساب).
    """

    def __init__(self, report_repository=None, account_repository=None) -> None:
        self._report_repo = report_repository
        self._account_repo = account_repository

    def _get_repo(self):
        """الحصول على الـ repository."""
        if self._report_repo is not None:
            return self._report_repo
        from adapters.repositories.sql_alchemy.report_repository import SqlAlchemyReportRepository
        self._report_repo = SqlAlchemyReportRepository()
        return self._report_repo

    async def execute(
        self,
        account_id: UUID,
        start_date: datetime,
        end_date: datetime,
        current_user=None,
    ) -> AccountStatementReport:
        """تنفيذ إصدار كشف حساب.

        Args:
            account_id: معرّف الحساب.
            start_date: بداية الفترة.
            end_date: نهاية الفترة.
            current_user: المستخدم الحالي.

        Returns:
            AccountStatementReport مع الرصيد الافتتاحي والحركات والرصيد الختامي.

        Raises:
            PermissionDeniedException: لو لم يكن لديك صلاحية.
            AccountNotFoundException: لو الحساب غير موجود.
        """
        from domain.value_objects.value_objects import Permission
        if current_user and not current_user.has_permission(Permission.REPORT_VIEW):
            from domain.exceptions.exceptions import PermissionDeniedException
            raise PermissionDeniedException("report.view")

        repo = self._get_repo()
        opening_balance, lines_raw, account_type = repo.get_account_statement_lines(
            account_id, start_date, end_date
        )

        # Get account info
        account_code = ""
        account_name = ""
        if self._account_repo is not None:
            account = await self._account_repo.get_by_id(account_id)
            if account:
                account_code = account.code
                account_name = account.name
        else:
            from adapters.repositories.sql_alchemy.account_journal_repository import SqlAlchemyAccountRepository
            acc_repo = SqlAlchemyAccountRepository()
            account = await acc_repo.get_by_id(account_id)
            if account:
                account_code = account.code
                account_name = account.name

        running_balance = opening_balance
        lines: list[AccountStatementLine] = []
        for r in lines_raw:
            dr = r["debit"]
            cr = r["credit"]
            if account_type.normal_balance == "DEBIT":
                running_balance += dr - cr
            else:
                running_balance += cr - dr
            lines.append(AccountStatementLine(
                date=r["date"],
                entry_no=r["entry_no"],
                description=r["description"],
                debit=dr,
                credit=cr,
                balance=running_balance,
            ))

        return AccountStatementReport(
            account_code=account_code,
            account_name=account_name,
            start_date=start_date,
            end_date=end_date,
            opening_balance=opening_balance,
            lines=lines,
            closing_balance=running_balance,
        )
