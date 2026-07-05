"""SQLAlchemy AuditLog model - سجل النشاط.

⚠️ Critical for security: append-only log of every sensitive operation.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.session import Base


class AuditLogModel(Base):
    """سجل النشاط - يحوي كل عملية حساسة في النظام.

    Append-only: لا يمكن تعديل أو حذف (تطبيقيًا عبر الـ application logic).
    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, POST, REVERSE, BACKUP, RESTORE
    entity_type: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    # customer, supplier, product, invoice, journal_entry, user, backup
    entity_id: Mapped[str] = mapped_column(String(36), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str] = mapped_column(String(50), default="")
    user_agent: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    def __repr__(self) -> str:
        return (
            f"<AuditLogModel(action={self.action!r}, "
            f"user={self.username!r}, entity={self.entity_type}/{self.entity_id})>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "description": self.description,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
