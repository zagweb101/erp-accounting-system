"""SQLAlchemy User model."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.session import Base


class UserModel(Base):
    """نموذج المستخدم في قاعدة البيانات."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(50), default="ACCOUNTANT")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_login_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    locked_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, username={self.username!r}, role={self.role})>"
