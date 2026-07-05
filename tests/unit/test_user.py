"""
اختبارات كيان المستخدم والمصادقة
"""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from domain.entities.user import User, UserStatus
from domain.exceptions.exceptions import (
    AccountLockedException,
    InvalidCredentialsException,
    PermissionDeniedException,
    UsernameAlreadyExistsException,
    ValidationException,
)
from domain.value_objects.value_objects import Permission, UserRole
from use_cases.auth.auth_use_cases import (
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    PasswordHasher,
)


class TestPasswordHasher:
    """اختبارات تشفير كلمات المرور."""

    def test_hash_and_verify_success(self) -> None:
        """تشفير ثم تحقق ناجح."""
        password = "MySecurePass@123"
        hashed = PasswordHasher.hash(password)
        assert hashed != password
        assert PasswordHasher.verify(password, hashed) is True

    def test_verify_wrong_password(self) -> None:
        """التحقق من كلمة مرور خاطئة يُعيد False."""
        hashed = PasswordHasher.hash("correctPassword")
        assert PasswordHasher.verify("wrongPassword", hashed) is False

    def test_short_password_rejected(self) -> None:
        """كلمة المرور القصيرة مرفوضة."""
        with pytest.raises(ValidationException, match="at least 8"):
            PasswordHasher.hash("short")

    def test_empty_password_rejected(self) -> None:
        """كلمة المرور الفارغة مرفوضة."""
        with pytest.raises(ValidationException):
            PasswordHasher.hash("")

    def test_hash_is_unique(self) -> None:
        """كل تشفير يُنتج hash مختلف (بسبب salt)."""
        h1 = PasswordHasher.hash("SamePassword@1")
        h2 = PasswordHasher.hash("SamePassword@1")
        assert h1 != h2


class TestUserEntity:
    """اختبارات كيان المستخدم."""

    def _create_user(self, role: UserRole = UserRole.ACCOUNTANT) -> User:
        return User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="dummyhash",
            full_name="Test User",
            role=role,
            status=UserStatus.ACTIVE,
        )

    def test_create_user_success(self) -> None:
        """إنشاء مستخدم صحيح يعمل."""
        user = self._create_user()
        assert user.username == "testuser"
        assert user.is_active()
        assert not user.is_locked()

    def test_username_too_short(self) -> None:
        """اسم المستخدم القصير مرفوض."""
        with pytest.raises(ValueError, match="at least 3"):
            User(username="ab", email="t@e.com", password_hash="h")

    def test_username_invalid_chars(self) -> None:
        """أحرف غير صالحة في اسم المستخدم مرفوضة."""
        with pytest.raises(ValueError, match="alphanumeric"):
            User(username="user@name", email="t@e.com", password_hash="h")

    def test_permission_check_accountant(self) -> None:
        """المحاسب لديه صلاحيات محددة."""
        user = self._create_user(role=UserRole.ACCOUNTANT)
        assert user.has_permission(Permission.CUSTOMER_CREATE)
        assert user.has_permission(Permission.INVOICE_CREATE)
        # Cannot manage users
        assert not user.has_permission(Permission.USER_CREATE)
        # Cannot change settings
        assert not user.has_permission(Permission.SETTINGS_UPDATE)

    def test_permission_check_admin(self) -> None:
        """المدير لديه كل الصلاحيات."""
        user = self._create_user(role=UserRole.ADMIN)
        assert user.has_permission(Permission.USER_CREATE)
        assert user.has_permission(Permission.USER_DELETE)
        assert user.has_permission(Permission.SETTINGS_UPDATE)

    def test_permission_check_owner(self) -> None:
        """صاحب الشركة لديه صلاحيات عرض فقط (لا إنشاء)."""
        user = self._create_user(role=UserRole.COMPANY_OWNER)
        assert user.has_permission(Permission.REPORT_VIEW)
        assert user.has_permission(Permission.BACKUP_CREATE)
        # Cannot create customers
        assert not user.has_permission(Permission.CUSTOMER_CREATE)

    def test_permission_check_disabled_user(self) -> None:
        """المستخدم المعطّل لا تُحتسب صلاحياته."""
        user = self._create_user()
        user.disable()
        assert not user.has_permission(Permission.CUSTOMER_VIEW)

    def test_failed_login_locks_account(self) -> None:
        """5 محاولات فاشلة تقفل الحساب."""
        user = self._create_user()
        for _ in range(User.MAX_FAILED_ATTEMPTS):
            user.record_failed_login()
        assert user.is_locked()
        assert user.status == UserStatus.LOCKED

    def test_successful_login_resets_counters(self) -> None:
        """الدخول الناجح يصفّر العدادات."""
        user = self._create_user()
        user.record_failed_login()
        user.record_failed_login()
        assert user.failed_login_attempts == 2

        user.record_successful_login()
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert user.last_login_at is not None
        assert user.status == UserStatus.ACTIVE

    def test_unlock(self) -> None:
        """فتح قفل الحساب يدويًا."""
        user = self._create_user()
        for _ in range(User.MAX_FAILED_ATTEMPTS):
            user.record_failed_login()
        assert user.is_locked()

        user.unlock()
        assert not user.is_locked()
        assert user.status == UserStatus.ACTIVE

    def test_safe_dict_excludes_password(self) -> None:
        """to_safe_dict لا يُخرج كلمة المرور."""
        user = self._create_user()
        d = user.to_safe_dict()
        assert "password_hash" not in d
        assert "password" not in d
        assert d["username"] == "testuser"

    def test_repr_excludes_password(self) -> None:
        """__repr__ لا يُظهر كلمة المرور."""
        user = User(
            username="test",
            email="t@e.com",
            password_hash="secret_hash",
        )
        repr_str = repr(user)
        assert "secret_hash" not in repr_str
        assert "test" in repr_str
