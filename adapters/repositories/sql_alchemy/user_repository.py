"""
SQLAlchemy User Repository Implementation

يحوّل طلبات الـ Use Case إلى استعلامات SQLAlchemy،
ويعيد الـ Domain Entities (User) بدلًا من الـ ORM Models.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.entities.user import User, UserStatus
from domain.value_objects.value_objects import UserRole
from infrastructure.db.models.user_model import UserModel
from infrastructure.db.session import session_scope
from use_cases.repositories.interfaces import IUserRepository


class SqlAlchemyUserRepository(IUserRepository):
    """تنفيذ مستودع المستخدمين بـ SQLAlchemy."""

    def _to_entity(self, model: UserModel) -> User:
        """تحويل ORM model إلى Domain entity."""
        return User(
            id=UUID(model.id),
            username=model.username,
            email=model.email,
            password_hash=model.password_hash,
            full_name=model.full_name,
            role=UserRole(model.role),
            status=UserStatus(model.status),
            failed_login_attempts=model.failed_login_attempts,
            last_login_at=model.last_login_at,
            locked_until=model.locked_until,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: User, model: UserModel | None = None) -> UserModel:
        """تحويل Domain entity إلى ORM model."""
        if model is None:
            model = UserModel(id=str(entity.id))
        model.username = entity.username
        model.email = entity.email
        model.password_hash = entity.password_hash
        model.full_name = entity.full_name
        model.role = entity.role.value
        model.status = entity.status.value
        model.failed_login_attempts = entity.failed_login_attempts
        model.last_login_at = entity.last_login_at
        model.locked_until = entity.locked_until
        model.updated_at = entity.updated_at
        return model

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        with session_scope() as session:
            stmt = select(UserModel).where(UserModel.id == str(user_id))
            model = session.execute(stmt).scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def get_by_username(self, username: str) -> Optional[User]:
        with session_scope() as session:
            stmt = select(UserModel).where(UserModel.username == username)
            model = session.execute(stmt).scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def save(self, user: User) -> User:
        with session_scope() as session:
            # Try to find existing
            stmt = select(UserModel).where(UserModel.id == str(user.id))
            existing = session.execute(stmt).scalar_one_or_none()
            model = self._to_model(user, existing)
            session.add(model)
            session.flush()  # ensure ID is generated
            session.refresh(model)
            return self._to_entity(model)

    async def delete(self, user_id: UUID) -> bool:
        with session_scope() as session:
            stmt = select(UserModel).where(UserModel.id == str(user_id))
            model = session.execute(stmt).scalar_one_or_none()
            if model is None:
                return False
            session.delete(model)
            return True

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        with session_scope() as session:
            stmt = (
                select(UserModel)
                .order_by(UserModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            models = session.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]
