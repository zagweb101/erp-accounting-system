"""SQLAlchemy Account model (دليل الحسابات)."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.session import Base


class AccountModel(Base):
    """نموذج الحساب المحاسبي."""

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), default="")
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)  # ASSET/LIABILITY/...
    parent_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_posting_account: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<AccountModel(code={self.code!r}, name={self.name!r})>"
