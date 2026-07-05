"""
اختبارات كائنات القيمة (Value Objects)
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from domain.exceptions.exceptions import (
    NegativeAmountException,
    ValidationException,
)
from domain.value_objects.value_objects import (
    AccountCode,
    AccountType,
    Money,
    Quantity,
)


class TestMoney:
    """اختبارات كائن قيمة Money."""

    def test_create_money(self) -> None:
        money = Money(Decimal("100.50"), "SAR")
        assert money.amount == Decimal("100.50")
        assert money.currency == "SAR"

    def test_create_money_from_float(self) -> None:
        money = Money.from_float(99.99)
        assert money.amount == Decimal("99.99")

    def test_create_money_from_int(self) -> None:
        money = Money.from_float(100)
        assert money.amount == Decimal("100")

    def test_zero_money(self) -> None:
        money = Money.zero()
        assert money.amount == Decimal("0")
        assert money.is_zero()

    def test_negative_money_rejected(self) -> None:
        with pytest.raises(NegativeAmountException):
            Money(Decimal("-100"))

    def test_invalid_currency_rejected(self) -> None:
        with pytest.raises(ValidationException, match="3-letter"):
            Money(Decimal("100"), "S")

    def test_add_same_currency(self) -> None:
        m1 = Money.from_float(100)
        m2 = Money.from_float(50)
        result = m1.add(m2)
        assert result.amount == Decimal("150")
        assert result.currency == "SAR"

    def test_add_different_currency_raises(self) -> None:
        m1 = Money(Decimal("100"), "SAR")
        m2 = Money(Decimal("50"), "USD")
        with pytest.raises(ValidationException, match="currency mismatch"):
            m1.add(m2)

    def test_subtract_success(self) -> None:
        m1 = Money.from_float(100)
        m2 = Money.from_float(30)
        result = m1.subtract(m2)
        assert result.amount == Decimal("70")

    def test_subtract_to_negative_raises(self) -> None:
        m1 = Money.from_float(30)
        m2 = Money.from_float(100)
        with pytest.raises(NegativeAmountException):
            m1.subtract(m2)

    def test_multiply(self) -> None:
        m = Money.from_float(50)
        result = m.multiply(3)
        assert result.amount == Decimal("150")

    def test_multiply_negative_raises(self) -> None:
        m = Money.from_float(50)
        with pytest.raises(NegativeAmountException):
            m.multiply(-1)

    def test_is_positive(self) -> None:
        assert Money.from_float(100).is_positive()
        assert not Money.zero().is_positive()
        assert not Money.from_float(0).is_positive()

    def test_format(self) -> None:
        m = Money.from_float(1234.56, "SAR")
        formatted = m.format()
        assert "1,234.56" in formatted
        assert "SAR" in formatted


class TestQuantity:
    """اختبارات كائن قيمة Quantity."""

    def test_create_quantity(self) -> None:
        q = Quantity(Decimal("5"), "piece")
        assert q.value == Decimal("5")
        assert q.unit == "piece"

    def test_negative_quantity_rejected(self) -> None:
        with pytest.raises(NegativeAmountException):
            Quantity(Decimal("-1"))

    def test_add_same_unit(self) -> None:
        q1 = Quantity(Decimal("5"), "kg")
        q2 = Quantity(Decimal("3"), "kg")
        result = q1.add(q2)
        assert result.value == Decimal("8")

    def test_add_different_unit_raises(self) -> None:
        q1 = Quantity(Decimal("5"), "kg")
        q2 = Quantity(Decimal("3"), "liter")
        with pytest.raises(ValidationException, match="unit mismatch"):
            q1.add(q2)


class TestAccountCode:
    """اختبارات كائن قيمة AccountCode."""

    def test_create_code(self) -> None:
        code = AccountCode("1101")
        assert code.value == "1101"
        assert code.level == 4

    def test_empty_code_rejected(self) -> None:
        with pytest.raises(ValidationException, match="empty"):
            AccountCode("")

    def test_non_digit_code_rejected(self) -> None:
        with pytest.raises(ValidationException, match="digits only"):
            AccountCode("11AB")

    def test_too_long_code_rejected(self) -> None:
        with pytest.raises(ValidationException, match="1-10"):
            AccountCode("12345678901")  # 11 digits

    def test_parent_code(self) -> None:
        code = AccountCode("1101")
        parent = code.parent_code
        assert parent is not None
        assert str(parent) == "110"

        grandparent = parent.parent_code
        assert grandparent is not None
        assert str(grandparent) == "11"

    def test_top_level_no_parent(self) -> None:
        code = AccountCode("1")
        assert code.parent_code is None

    def test_is_child_of(self) -> None:
        child = AccountCode("1101")
        parent = AccountCode("11")
        assert child.is_child_of(parent)
        assert not parent.is_child_of(child)

    def test_is_not_child_of_unrelated(self) -> None:
        code = AccountCode("1101")
        unrelated = AccountCode("21")
        assert not code.is_child_of(unrelated)


class TestAccountType:
    """اختبارات نوع الحساب."""

    def test_normal_balance(self) -> None:
        assert AccountType.ASSET.normal_balance == "DEBIT"
        assert AccountType.EXPENSE.normal_balance == "DEBIT"
        assert AccountType.LIABILITY.normal_balance == "CREDIT"
        assert AccountType.EQUITY.normal_balance == "CREDIT"
        assert AccountType.REVENUE.normal_balance == "CREDIT"

    def test_arabic_names(self) -> None:
        assert AccountType.ASSET.arabic_name == "أصول"
        assert AccountType.LIABILITY.arabic_name == "خصوم"
        assert AccountType.EQUITY.arabic_name == "حقوق ملكية"
        assert AccountType.REVENUE.arabic_name == "إيرادات"
        assert AccountType.EXPENSE.arabic_name == "مصروفات"
