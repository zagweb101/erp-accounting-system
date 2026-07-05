"""SQLAlchemy Journal Entry & Lines models."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Numeric, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.session import Base


class JournalEntryModel(Base):
    """نموذج القيد المحاسبي."""

    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    entry_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    reference_type: Mapped[str] = mapped_column(String(20), default="MANUAL")
    reference_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    posted_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    lines: Mapped[list["JournalLineModel"]] = relationship(
        "JournalLineModel",
        back_populates="entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<JournalEntryModel(entry_no={self.entry_no!r}, status={self.status})>"


class JournalLineModel(Base):
    """نموذج بند القيد."""

    __tablename__ = "journal_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.id"), nullable=False, index=True
    )
    debit: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    credit: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    entry: Mapped["JournalEntryModel"] = relationship("JournalEntryModel", back_populates="lines")

    def __repr__(self) -> str:
        side = "DR" if self.debit > 0 else "CR"
        amt = self.debit if self.debit > 0 else self.credit
        return f"<JournalLineModel(account_id={self.account_id}, {side}={amt})>"
