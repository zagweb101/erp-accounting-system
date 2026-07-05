"""
Audit Service - خدمة سجل النشاط

Append-only log for every sensitive operation.
Critical for security and compliance (PDPL, SOCPA).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from infrastructure.db.models.audit_log_model import AuditLogModel
from infrastructure.db.session import session_scope


class AuditService:
    """خدمة تسجيل العمليات الحساسة في سجل النشاط.

    Append-only: لا توجد دالة update أو delete - فقط record().
    """

    def record(
        self,
        user_id: Optional[UUID],
        username: Optional[str],
        action: str,  # CREATE, UPDATE, DELETE, LOGIN, POST, REVERSE, etc.
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        description: str = "",
        ip_address: str = "",
        user_agent: str = "",
    ) -> AuditLogModel:
        """تسجيل عملية في سجل النشاط.

        ⚠️ هذه الدالة لا ترمي استثناء عند الفشل - سجل النشاط لا يجب أن
        يوقف العمليات التجارية. الأخطاء تُسجّل في log فقط.
        """
        try:
            with session_scope() as s:
                log = AuditLogModel(
                    id=str(UUID(int=0)) if False else str(__import__('uuid').uuid4()),
                    user_id=str(user_id) if user_id else None,
                    username=username,
                    action=action,
                    entity_type=entity_type,
                    entity_id=str(entity_id) if entity_id else None,
                    description=description,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                s.add(log)
                s.flush()
                s.refresh(log)
                # Detach to use outside session
                s.expunge(log)
                return log
        except Exception as e:
            # Don't fail the operation if audit fails - but log the error
            # In production: use logger.error() here
            print(f"⚠️ AUDIT LOG FAILED: {e}")
            return None  # type: ignore

    def list_logs(
        self,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLogModel]:
        """سرد سجلات النشاط (للمدير)."""
        from sqlalchemy import and_

        with session_scope() as s:
            stmt = select(AuditLogModel).order_by(
                AuditLogModel.created_at.desc()
            )
            conditions = []
            if user_id:
                conditions.append(AuditLogModel.user_id == str(user_id))
            if action:
                conditions.append(AuditLogModel.action == action)
            if entity_type:
                conditions.append(AuditLogModel.entity_type == entity_type)
            if start_date:
                conditions.append(AuditLogModel.created_at >= start_date)
            if end_date:
                conditions.append(AuditLogModel.created_at <= end_date)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            stmt = stmt.offset(skip).limit(limit)
            models = s.execute(stmt).scalars().all()
            # Detach
            for m in models:
                s.expunge(m)
            return list(models)

    def count_logs(
        self,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
    ) -> int:
        """عدد السجلات (للإحصائيات)."""
        with session_scope() as s:
            stmt = select(func.count(AuditLogModel.id))
            if user_id:
                stmt = stmt.where(AuditLogModel.user_id == str(user_id))
            if action:
                stmt = stmt.where(AuditLogModel.action == action)
            return s.execute(stmt).scalar() or 0


# Singleton instance
audit_service = AuditService()
