"""
Authentication Use Cases - حالات استخدام المصادقة

كل حالة استخدام = ملف واحد يحوي كلاسًا واحدًا بـ method واحدة (execute).
تستخدم Repository interfaces (لا تعرف عن SQLAlchemy أو قاعدة البيانات).
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import bcrypt

from domain.entities.user import User, UserStatus
from domain.exceptions.exceptions import (
    AccountLockedException,
    InvalidCredentialsException,
    PermissionDeniedException,
    UserNotFoundException,
    UsernameAlreadyExistsException,
    ValidationException,
)
from domain.value_objects.value_objects import UserRole
from use_cases.repositories.interfaces import IUserRepository


# ============================================================
# Password hashing (bcrypt wrapper)
# ============================================================
class PasswordHasher:
    """تشفير كلمات المرور بـ bcrypt (cost factor 12)."""

    BCRYPT_COST = 12

    @staticmethod
    def hash(password: str) -> str:
        if not password or len(password) < 8:
            raise ValidationException(
                "password", "must be at least 8 characters"
            )
        salt = bcrypt.gensalt(rounds=PasswordHasher.BCRYPT_COST)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify(password: str, password_hash: str) -> bool:
        if not password or not password_hash:
            return False
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False


# ============================================================
# DTOs (Data Transfer Objects)
# ============================================================
@dataclass
class LoginRequest:
    username: str
    password: str


@dataclass
class LoginResponse:
    user: User
    token: str  # simple session token (JWT in v1.5)
    expires_at: datetime


@dataclass
class CreateUserRequest:
    username: str
    password: str
    email: str
    full_name: str
    role: UserRole = UserRole.ACCOUNTANT


# ============================================================
# Use Case: Login
# ============================================================
class LoginUseCase:
    """حالة استخدام تسجيل الدخول.

    تتلقى طلبًا، تتحقق من البيانات، تُعيد المستخدم + التوكن.
    """

    SESSION_DURATION_HOURS = 8

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, request: LoginRequest) -> LoginResponse:
        # 1. التحقق من المدخلات
        if not request.username or not request.password:
            raise ValidationException(
                "credentials", "username and password are required"
            )

        # 2. البحث عن المستخدم
        user = await self._user_repo.get_by_username(request.username)
        if user is None:
            # لا نكشف أن المستخدم غير موجود (أمان)
            raise InvalidCredentialsException()

        # 3. التحقق من قفل الحساب
        if user.is_locked():
            unlock_at = user.locked_until.isoformat() if user.locked_until else None
            raise AccountLockedException(unlock_at)

        # 4. التحقق من حالة الحساب
        if user.status == UserStatus.DISABLED:
            raise AccountLockedException()

        # 5. التحقق من كلمة المرور
        if not PasswordHasher.verify(request.password, user.password_hash):
            user.record_failed_login()
            await self._user_repo.save(user)
            raise InvalidCredentialsException()

        # 6. تسجيل الدخول الناجح
        user.record_successful_login()
        await self._user_repo.save(user)

        # 7. توليد session token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=self.SESSION_DURATION_HOURS)

        return LoginResponse(user=user, token=token, expires_at=expires_at)


# ============================================================
# Use Case: Create User
# ============================================================
class CreateUserUseCase:
    """حالة استخدام إنشاء مستخدم جديد (للمدير فقط)."""

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def execute(
        self, request: CreateUserRequest, current_user: User
    ) -> User:
        # 1. التحقق من الصلاحية
        from domain.value_objects.value_objects import Permission
        if not current_user.has_permission(Permission.USER_CREATE):
            raise PermissionDeniedException("user.create")

        # 2. التحقق من عدم تكرار اسم المستخدم
        existing = await self._user_repo.get_by_username(request.username)
        if existing is not None:
            raise UsernameAlreadyExistsException(request.username)

        # 3. التحقق من صحة المدخلات
        if not request.email or "@" not in request.email:
            raise ValidationException("email", "invalid email format")

        # 4. تشفير كلمة المرور
        password_hash = PasswordHasher.hash(request.password)

        # 5. إنشاء المستخدم
        user = User(
            username=request.username,
            email=request.email,
            password_hash=password_hash,
            full_name=request.full_name,
            role=request.role,
            status=UserStatus.ACTIVE,
        )

        # 6. الحفظ
        return await self._user_repo.save(user)


# ============================================================
# Use Case: Change Password
# ============================================================
@dataclass
class ChangePasswordRequest:
    user_id: UUID
    current_password: str
    new_password: str


class ChangePasswordUseCase:
    """حالة استخدام تغيير كلمة المرور."""

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, request: ChangePasswordRequest) -> User:
        # 1. البحث عن المستخدم
        user = await self._user_repo.get_by_id(request.user_id)
        if user is None:
            raise UserNotFoundException(str(request.user_id))

        # 2. التحقق من كلمة المرور الحالية
        if not PasswordHasher.verify(request.current_password, user.password_hash):
            raise InvalidCredentialsException()

        # 3. تشفير كلمة المرور الجديدة
        user.password_hash = PasswordHasher.hash(request.new_password)
        user.updated_at = datetime.now()

        # 4. الحفظ
        return await self._user_repo.save(user)


# ============================================================
# Use Case: Reset Password (admin)
# ============================================================
@dataclass
class ResetPasswordRequest:
    target_user_id: UUID
    admin_user_id: UUID


class ResetPasswordUseCase:
    """حالة استخدام إعادة تعيين كلمة المرور (للمدير).

    تولّد كلمة مرور مؤقتة عشوائية، تُجبر المستخدم على تغييرها عند الدخول.
    """

    TEMP_PASSWORD_LENGTH = 12

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, request: ResetPasswordRequest, admin: User) -> str:
        """تُعيد كلمة المرور المؤقتة (لإرسالها للمستخدم)."""
        # 1. التحقق من صلاحية المدير
        from domain.value_objects.value_objects import Permission
        if not admin.has_permission(Permission.USER_UPDATE):
            raise PermissionDeniedException("user.update")

        # 2. البحث عن المستخدم المستهدف
        user = await self._user_repo.get_by_id(request.target_user_id)
        if user is None:
            raise UserNotFoundException(str(request.target_user_id))

        # 3. توليد كلمة مرور مؤقتة
        temp_password = secrets.token_urlsafe(self.TEMP_PASSWORD_LENGTH)[:self.TEMP_PASSWORD_LENGTH]

        # 4. تشفيرها
        user.password_hash = PasswordHasher.hash(temp_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.status = UserStatus.ACTIVE
        user.updated_at = datetime.now()

        # 5. الحفظ
        await self._user_repo.save(user)

        return temp_password


# ============================================================
# Use Case: Unlock User
# ============================================================
class UnlockUserUseCase:
    """حالة استخدام فتح قفل حساب (للمدير)."""

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, target_user_id: UUID, admin: User) -> User:
        from domain.value_objects.value_objects import Permission
        if not admin.has_permission(Permission.USER_UPDATE):
            raise PermissionDeniedException("user.update")

        user = await self._user_repo.get_by_id(target_user_id)
        if user is None:
            raise UserNotFoundException(str(target_user_id))

        user.unlock()
        return await self._user_repo.save(user)
