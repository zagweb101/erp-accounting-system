"""
User Entity - كيان المستخدم

كيان مستقل عن قاعدة البيانات وواجهة المستخدم.
يحوي قواعد العمل المتأصلة في مفهوم المستخدم.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from domain.value_objects.value_objects import Permission, UserRole


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    DISABLED = "DISABLED"


@dataclass
class User:
    """كيان المستخدم في النظام.

    الحقول الحساسة (password_hash) لا تُخرَج في الـ __repr__.
    """

    id: UUID = field(default_factory=uuid4)
    username: str = ""
    email: str = ""
    password_hash: str = ""  # bcrypt hash, never plain text
    full_name: str = ""
    role: UserRole = UserRole.ACCOUNTANT
    status: UserStatus = UserStatus.ACTIVE
    failed_login_attempts: int = 0
    last_login_at: Optional[datetime] = None
    locked_until: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Business rules
    MAX_FAILED_ATTEMPTS = 5
    LOCK_DURATION_MINUTES = 15

    def __post_init__(self) -> None:
        if not self.username:
            raise ValueError("username is required")
        if len(self.username) < 3:
            raise ValueError("username must be at least 3 characters")
        if not self.username.replace("_", "").replace(".", "").isalnum():
            raise ValueError("username must be alphanumeric (with _ or . allowed)")

    # ============================================================
    # Permission checks (RBAC)
    # ============================================================
    def has_permission(self, permission: Permission) -> bool:
        """هل المستخدم لديه صلاحية معينة؟"""
        from domain.value_objects.value_objects import ROLE_PERMISSIONS
        if self.status != UserStatus.ACTIVE:
            return False
        role_perms = ROLE_PERMISSIONS.get(self.role, frozenset())
        return permission in role_perms

    def has_any_permission(self, *permissions: Permission) -> bool:
        """هل المستخدم لديه أي صلاحية من القائمة؟"""
        return any(self.has_permission(p) for p in permissions)

    def has_all_permissions(self, *permissions: Permission) -> bool:
        """هل المستخدم لديه كل الصلاحيات المطلوبة؟"""
        return all(self.has_permission(p) for p in permissions)

    # ============================================================
    # Authentication state
    # ============================================================
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    def is_locked(self) -> bool:
        """هل الحساب مقفل حاليًا؟"""
        if self.status == UserStatus.LOCKED:
            return True
        if self.locked_until and self.locked_until > datetime.now():
            return True
        return False

    def record_failed_login(self) -> None:
        """تسجيل محاولة فاشلة، مع قفل الحساب عند تجاوز الحد."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= self.MAX_FAILED_ATTEMPTS:
            from datetime import timedelta
            self.locked_until = datetime.now() + timedelta(
                minutes=self.LOCK_DURATION_MINUTES
            )
            self.status = UserStatus.LOCKED
        self.updated_at = datetime.now()

    def record_successful_login(self) -> None:
        """تسجيل دخول ناجح: تصفير العدادات وتحديث الوقت."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.status = UserStatus.ACTIVE
        self.last_login_at = datetime.now()
        self.updated_at = datetime.now()

    def unlock(self) -> None:
        """فتح قفل الحساب يدويًا (بواسطة مدير)."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now()

    def disable(self) -> None:
        """تعطيل الحساب (لا يمكنه الدخول)."""
        self.status = UserStatus.DISABLED
        self.updated_at = datetime.now()

    # ============================================================
    # Sensitive data protection
    # ============================================================
    def __repr__(self) -> str:
        return (
            f"User(id={self.id}, username={self.username!r}, "
            f"role={self.role}, status={self.status})"
        )

    def to_safe_dict(self) -> dict:
        """تمثيل آمن بدون بيانات حساسة (للعرض والتسجيل)."""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "status": self.status.value,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat(),
        }
