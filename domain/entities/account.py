"""
Account Entity - كيان الحساب المحاسبي

يمثل حسابًا في دليل الحسابات (Chart of Accounts).
مثلًا: 1101 (الصندوق)، 2101 (ذمم الموردين)، 4101 (المبيعات).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from domain.exceptions.exceptions import AccountTypeException
from domain.value_objects.value_objects import AccountCode, AccountType, Money


@dataclass
class Account:
    """كيان الحساب المحاسبي."""

    id: UUID = field(default_factory=uuid4)
    code: AccountCode = None  # type: ignore
    name: str = ""
    name_en: str = ""
    account_type: AccountType = AccountType.ASSET
    parent_id: Optional[UUID] = None
    is_active: bool = True
    is_posting_account: bool = True  # هل يقبل قيود؟ (الحسابات الرئيسية لا)
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.code is None:
            raise ValueError("account code is required")
        if not self.name:
            raise ValueError("account name is required")
        if not isinstance(self.account_type, AccountType):
            raise AccountTypeException(str(self.account_type))

    @property
    def normal_balance(self) -> str:
        """الطبيعة الطبيعية للرصيد: DEBIT أو CREDIT."""
        return self.account_type.normal_balance

    def is_balance_sheet_account(self) -> bool:
        """هل الحساب يظهر في الميزانية العمومية؟ (أصول/خصوم/حقوق ملكية)."""
        return self.account_type in (
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        )

    def is_income_statement_account(self) -> bool:
        """هل الحساب يظهر في قائمة الدخل؟ (إيرادات/مصروفات)."""
        return self.account_type in (AccountType.REVENUE, AccountType.EXPENSE)

    def is_temporary_account(self) -> bool:
        """هل الحساب مؤقت (يُقفَل نهاية السنة)؟"""
        return self.is_income_statement_account()

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "code": str(self.code),
            "name": self.name,
            "name_en": self.name_en,
            "account_type": self.account_type.value,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "is_active": self.is_active,
            "is_posting_account": self.is_posting_account,
            "description": self.description,
        }
