"""
اختبارات وحدة القيد المزدوج (Journal Entry)

تتحقق من:
- القاعدة الذهبية: مدين = دائن
- رفض القيد غير المتوازن
- رفض تعديل قيد مرحّل
- القيد العكسي
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from domain.entities.journal import (
    JournalEntry,
    JournalEntryReferenceType,
    JournalEntryStatus,
    UnbalancedJournalEntryException as _unused,  # noqa
)
from domain.entities.journal import (
    JournalEntryAlreadyPostedException,
    JournalEntryReferenceType,
)
from domain.exceptions.exceptions import UnbalancedJournalEntryException


class TestJournalEntry:
    """اختبارات كيان القيد المحاسبي."""

    def _create_entry(self, entry_no: str = "JE-2026-000001") -> JournalEntry:
        """Helper لإنشاء قيد فارغ."""
        return JournalEntry(
            entry_no=entry_no,
            date=datetime.utcnow(),
            reference_type=JournalEntryReferenceType.MANUAL,
            description="test entry",
            created_by=uuid4(),
        )

    def test_create_empty_entry(self) -> None:
        """إنشاء قيد فارغ يعمل."""
        entry = self._create_entry()
        assert entry.entry_no == "JE-2026-000001"
        assert entry.status == JournalEntryStatus.DRAFT
        assert not entry.has_lines()
        assert entry.is_balanced()  # 0 = 0

    def test_add_balanced_lines(self) -> None:
        """إضافة بنود متوازنة تعمل."""
        entry = self._create_entry()
        account_id = uuid4()

        entry.add_line(account_id=account_id, debit=Decimal("1000"), description="debit line")
        entry.add_line(account_id=account_id, credit=Decimal("1000"), description="credit line")

        assert entry.line_count() == 2
        assert entry.total_debit() == Decimal("1000")
        assert entry.total_credit() == Decimal("1000")
        assert entry.is_balanced()
        assert entry.difference() == Decimal("0")

    def test_add_unbalanced_lines_raises(self) -> None:
        """القيد غير المتوازن يجب أن يُرفض عند الـ assert."""
        entry = self._create_entry()
        account_id = uuid4()

        entry.add_line(account_id=account_id, debit=Decimal("1000"))
        entry.add_line(account_id=account_id, credit=Decimal("500"))

        # Not balanced yet
        assert not entry.is_balanced()
        assert entry.difference() == Decimal("500")

        # Should raise when asserted
        with pytest.raises(UnbalancedJournalEntryException):
            entry.assert_balanced()

    def test_cannot_add_line_to_posted_entry(self) -> None:
        """لا يمكن إضافة بنود لقيد مرحّل."""
        entry = self._create_entry()
        account_id = uuid4()

        entry.add_line(account_id=account_id, debit=Decimal("100"))
        entry.add_line(account_id=account_id, credit=Decimal("100"))
        entry.post(posted_by=uuid4())

        with pytest.raises(JournalEntryAlreadyPostedException):
            entry.add_line(account_id=account_id, debit=Decimal("50"))

    def test_post_unbalanced_raises(self) -> None:
        """ترحيل قيد غير متوازن يرمي استثناء."""
        entry = self._create_entry()
        account_id = uuid4()

        entry.add_line(account_id=account_id, debit=Decimal("100"))
        entry.add_line(account_id=account_id, credit=Decimal("50"))  # not balanced

        with pytest.raises(UnbalancedJournalEntryException):
            entry.post(posted_by=uuid4())

    def test_post_empty_entry_raises(self) -> None:
        """ترحيل قيد فارغ يرمي استثناء."""
        entry = self._create_entry()
        with pytest.raises(ValueError, match="empty"):
            entry.post(posted_by=uuid4())

    def test_post_success(self) -> None:
        """ترحيل قيد متوازن بنجاح."""
        entry = self._create_entry()
        account_id = uuid4()
        posted_by = uuid4()

        entry.add_line(account_id=account_id, debit=Decimal("500"))
        entry.add_line(account_id=account_id, credit=Decimal("500"))
        entry.post(posted_by=posted_by)

        assert entry.status == JournalEntryStatus.POSTED
        assert entry.posted_by == posted_by
        assert entry.posted_at is not None

    def test_reverse_posted_entry(self) -> None:
        """قلب قيد مرحّل يُنشئ قيدًا عكسيًا متوازنًا."""
        entry = self._create_entry()
        account_id = uuid4()
        user_id = uuid4()

        entry.add_line(account_id=account_id, debit=Decimal("200"), description="original debit")
        entry.add_line(account_id=account_id, credit=Decimal("200"), description="original credit")
        entry.post(posted_by=user_id)

        # Reverse
        reversed_entry = entry.reverse(reversed_by=user_id)

        assert reversed_entry.is_balanced()
        assert reversed_entry.status == JournalEntryStatus.POSTED
        # Debit/credit should be swapped
        assert reversed_entry.total_debit() == Decimal("200")
        assert reversed_entry.total_credit() == Decimal("200")
        # Original entry status should be REVERSED
        assert entry.status == JournalEntryStatus.REVERSED

    def test_reverse_non_posted_raises(self) -> None:
        """قلب قيد غير مرحّل يرمي استثناء."""
        entry = self._create_entry()
        with pytest.raises(ValueError, match="only posted"):
            entry.reverse(reversed_by=uuid4())

    def test_validate_balanced_entry(self) -> None:
        """validate يُعيد قائمة فارغة للقيد الصحيح."""
        entry = self._create_entry()
        account_id = uuid4()
        entry.add_line(account_id=account_id, debit=Decimal("100"))
        entry.add_line(account_id=account_id, credit=Decimal("100"))
        errors = entry.validate()
        assert errors == []

    def test_validate_unbalanced_returns_errors(self) -> None:
        """validate يُعيد أخطاء للقيد غير المتوازن."""
        entry = self._create_entry()
        account_id = uuid4()
        entry.add_line(account_id=account_id, debit=Decimal("100"))
        entry.add_line(account_id=account_id, credit=Decimal("50"))
        errors = entry.validate()
        assert len(errors) > 0
        assert any("not balanced" in e for e in errors)

    def test_cannot_have_both_debit_and_credit_in_line(self) -> None:
        """بند القيد لا يمكن أن يكون مدينًا ودائنًا في آنٍ واحد."""
        entry = self._create_entry()
        with pytest.raises(ValueError, match="both debit and credit"):
            entry.add_line(
                account_id=uuid4(),
                debit=Decimal("100"),
                credit=Decimal("100"),
            )

    def test_negative_amounts_rejected(self) -> None:
        """المبالغ السالبة مرفوضة."""
        entry = self._create_entry()
        with pytest.raises(ValueError, match="negative"):
            entry.add_line(account_id=uuid4(), debit=Decimal("-100"))
