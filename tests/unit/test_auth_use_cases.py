"""
اختبارات شاملة لـ Auth Use Cases (رفع التغطية من 50% إلى 80%+)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.db.session import session_scope


from infrastructure.db.models.user_model import UserModel

from adapters.repositories.sql_alchemy.user_repository import SqlAlchemyUserRepository
from use_cases.auth.auth_use_cases import (
    ChangePasswordRequest, ChangePasswordUseCase, CreateUserRequest, CreateUserUseCase,
    LoginRequest, LoginUseCase, PasswordHasher, ResetPasswordRequest, ResetPasswordUseCase,
    UnlockUserUseCase,
)
from domain.entities.user import User, UserStatus
from domain.value_objects.value_objects import Permission, UserRole
from domain.exceptions.exceptions import (
    AccountLockedException, InvalidCredentialsException, PermissionDeniedException,
    UserNotFoundException, UsernameAlreadyExistsException, ValidationException,
)


@pytest.fixture
def repo():
    return SqlAlchemyUserRepository()


@pytest.fixture
def admin_user():
    """الحصول على مستخدم admin من DB."""
    from sqlalchemy import select
    with session_scope() as s:
        m = s.execute(select(UserModel).where(UserModel.username == "admin")).scalar_one()
        return User(
            id=m.id, username=m.username, email=m.email, password_hash=m.password_hash,
            full_name=m.full_name, role=UserRole(m.role), status=UserStatus(m.status),
        )


@pytest.fixture
def accountant_user(repo, admin_user):
    """إنشاء مستخدم محاسب للاختبار."""
    uc = CreateUserUseCase(repo)
    user = uc.execute(
        CreateUserRequest(
            username=f"accountant_{uuid4().hex[:8]}",
            password="Accountant@123",
            email=f"acc_{uuid4().hex[:8]}@test.com",
            full_name="Test Accountant",
            role=UserRole.ACCOUNTANT,
        ),
        current_user=admin_user,
    )
    # Execute is async - use asyncio
    import asyncio
    return asyncio.get_event_loop().run_until_complete(user)


class TestLoginUseCase:
    """اختبارات حالة استخدام تسجيل الدخول."""

    @pytest.mark.asyncio
    async def test_login_success(self, repo, admin_user):
        """تسجيل دخول ناجح ببيانات صحيحة."""
        # Create user
        create_uc = CreateUserUseCase(repo)
        user = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"login_test_{uuid4().hex[:8]}",
                password="Password@123",
                email=f"login_{uuid4().hex[:8]}@test.com",
                
            ),
            current_user=admin_user,
        )

        # Login
        login_uc = LoginUseCase(repo)
        response = await login_uc.execute(
            LoginRequest(username=user.username, password="Password@123")
        )
        assert response.user.id == user.id
        assert response.token is not None
        assert len(response.token) > 20

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, repo, admin_user):
        """تسجيل دخول بكلمة مرور خاطئة يفشل."""
        create_uc = CreateUserUseCase(repo)
        user = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"wrong_pass_{uuid4().hex[:8]}",
                password="CorrectPass@123",
                email=f"wp_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )

        login_uc = LoginUseCase(repo)
        with pytest.raises(InvalidCredentialsException):
            await login_uc.execute(
                LoginRequest(username=user.username, password="WrongPass@456")
            )

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, repo, admin_user):
        """تسجيل دخول لمستخدم غير موجود يفشل برسالة عامة."""
        login_uc = LoginUseCase(repo)
        with pytest.raises(InvalidCredentialsException):
            await login_uc.execute(
                LoginRequest(username="nonexistent_xyz", password="anything")
            )

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, repo, admin_user):
        """تسجيل دخول بحقول فارغة يفشل."""
        login_uc = LoginUseCase(repo)
        with pytest.raises(ValidationException):
            await login_uc.execute(LoginRequest(username="", password=""))

    @pytest.mark.asyncio
    async def test_login_locked_account(self, repo, admin_user):
        """تسجيل دخول لحساب مقفل يفشل."""
        create_uc = CreateUserUseCase(repo)
        user = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"locked_{uuid4().hex[:8]}",
                password="Password@123",
                email=f"locked_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )

        # Lock the account by triggering MAX_FAILED_ATTEMPTS failed logins
        # Each attempt raises InvalidCredentialsException (expected)
        for _ in range(User.MAX_FAILED_ATTEMPTS):
            with pytest.raises(InvalidCredentialsException):
                await LoginUseCase(repo).execute(
                    LoginRequest(username=user.username, password="wrong")
                )

        # Verify the account is now locked
        locked_user = await repo.get_by_username(user.username)
        assert locked_user.is_locked()

        # Now login (even with correct password) should fail with AccountLockedException
        login_uc = LoginUseCase(repo)
        with pytest.raises((AccountLockedException, InvalidCredentialsException)):
            await login_uc.execute(
                LoginRequest(username=user.username, password="Password@123")
            )

    @pytest.mark.asyncio
    async def test_login_disabled_account(self, repo, admin_user):
        """تسجيل دخول لحساب معطّل يفشل."""
        create_uc = CreateUserUseCase(repo)
        user = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"disabled_{uuid4().hex[:8]}",
                password="Password@123",
                email=f"disabled_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )

        # Disable the user
        user.disable()
        await repo.save(user)

        login_uc = LoginUseCase(repo)
        with pytest.raises((AccountLockedException, InvalidCredentialsException)):
            await login_uc.execute(
                LoginRequest(username=user.username, password="Password@123")
            )

    @pytest.mark.asyncio
    async def test_successful_login_resets_failed_attempts(self, repo, admin_user):
        """تسجيل دخول ناجح بعد محاولات فاشلة يصفّر العدّاد."""
        create_uc = CreateUserUseCase(repo)
        user = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"reset_{uuid4().hex[:8]}",
                password="Password@123",
                email=f"reset_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )

        # 3 failed attempts
        login_uc = LoginUseCase(repo)
        for _ in range(3):
            with pytest.raises(InvalidCredentialsException):
                await login_uc.execute(
                    LoginRequest(username=user.username, password="wrong")
                )

        # Verify failed count
        user_before = await repo.get_by_username(user.username)
        assert user_before.failed_login_attempts == 3

        # Successful login
        response = await login_uc.execute(
            LoginRequest(username=user.username, password="Password@123")
        )
        assert response.user.failed_login_attempts == 0
        assert response.user.last_login_at is not None


class TestCreateUserUseCase:
    """اختبارات حالة استخدام إنشاء مستخدم."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, repo, admin_user):
        """إنشاء مستخدم جديد بنجاح."""
        uc = CreateUserUseCase(repo)
        user = await uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"new_user_{uuid4().hex[:8]}",
                password="NewPass@123",
                email=f"new_{uuid4().hex[:8]}@test.com",
                
                role=UserRole.ACCOUNTANT,
            ),
            current_user=admin_user,
        )
        assert user.id is not None
        assert user.password_hash != "NewPass@123"  # hashed
        assert PasswordHasher.verify("NewPass@123", user.password_hash)

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, repo, admin_user):
        """اسم مستخدم مكرر يفشل."""
        uc = CreateUserUseCase(repo)
        username = f"dup_{uuid4().hex[:8]}"
        await uc.execute(
            CreateUserRequest(
                username=username, password="Pass@123",
                full_name="Test User",
                email=f"dup1_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )

        with pytest.raises(UsernameAlreadyExistsException):
            await uc.execute(
                CreateUserRequest(
                    username=username, password="Pass@123",
                    full_name="Test User",
                email=f"dup2_{uuid4().hex[:8]}@test.com",
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_user_invalid_email(self, repo, admin_user):
        """بريد إلكتروني غير صالح يفشل."""
        uc = CreateUserUseCase(repo)
        with pytest.raises(ValidationException, match="invalid email"):
            await uc.execute(
                CreateUserRequest(
                    full_name="Test User",
                    username=f"bad_email_{uuid4().hex[:8]}",
                    password="Pass@123",
                    email="invalid-email",
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_user_short_password(self, repo, admin_user):
        """كلمة مرور قصيرة يفشل."""
        uc = CreateUserUseCase(repo)
        with pytest.raises(ValidationException, match="at least 8"):
            await uc.execute(
                CreateUserRequest(
                    full_name="Test User",
                    username=f"short_pass_{uuid4().hex[:8]}",
                    password="short",
                    email=f"sp_{uuid4().hex[:8]}@test.com",
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_user_by_non_admin_fails(self, repo, admin_user):
        """محاسب لا يمكنه إنشاء مستخدمين."""
        # Create accountant
        create_uc = CreateUserUseCase(repo)
        accountant = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"acc_create_{uuid4().hex[:8]}",
                password="Pass@123",
                email=f"acc_{uuid4().hex[:8]}@test.com",
                role=UserRole.ACCOUNTANT,
            ),
            current_user=admin_user,
        )

        # Accountant tries to create user
        with pytest.raises(PermissionDeniedException):
            await create_uc.execute(
                CreateUserRequest(
                    full_name="Test User",
                    username=f"by_acc_{uuid4().hex[:8]}",
                    password="Pass@123",
                    email=f"by_acc_{uuid4().hex[:8]}@test.com",
                ),
                current_user=accountant,
            )

    @pytest.mark.asyncio
    async def test_create_user_all_roles(self, repo, admin_user):
        """إنشاء مستخدمين بكل الأدوار."""
        uc = CreateUserUseCase(repo)
        for role in UserRole:
            user = await uc.execute(
                CreateUserRequest(
                    username=f"role_{role.value}_{uuid4().hex[:8]}",
                    password="Pass@123",
                    email=f"role_{role.value}_{uuid4().hex[:8]}@test.com",
                    full_name=f"Test {role.value}",
                    role=role,
                ),
                current_user=admin_user,
            )
            assert user.role == role
            assert user.status == UserStatus.ACTIVE


class TestChangePasswordUseCase:
    """اختبارات تغيير كلمة المرور."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, repo, admin_user):
        """تغيير كلمة المرور بنجاح."""
        create_uc = CreateUserUseCase(repo)
        user = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"change_{uuid4().hex[:8]}",
                password="OldPass@123",
                email=f"change_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )

        uc = ChangePasswordUseCase(repo)
        updated = await uc.execute(
            ChangePasswordRequest(
                user_id=user.id,
                current_password="OldPass@123",
                new_password="NewPass@456",
            )
        )
        assert PasswordHasher.verify("NewPass@456", updated.password_hash)
        assert not PasswordHasher.verify("OldPass@123", updated.password_hash)

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, repo, admin_user):
        """تغيير كلمة المرور بكلمة حالية خاطئة يفشل."""
        create_uc = CreateUserUseCase(repo)
        user = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"wrong_curr_{uuid4().hex[:8]}",
                password="OldPass@123",
                email=f"wc_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )

        uc = ChangePasswordUseCase(repo)
        with pytest.raises(InvalidCredentialsException):
            await uc.execute(
                ChangePasswordRequest(
                    user_id=user.id,
                    current_password="WrongPass",
                    new_password="NewPass@456",
                )
            )

    @pytest.mark.asyncio
    async def test_change_password_nonexistent_user(self, repo, admin_user):
        """تغيير كلمة مرور لمستخدم غير موجود يفشل."""
        uc = ChangePasswordUseCase(repo)
        with pytest.raises(UserNotFoundException):
            await uc.execute(
                ChangePasswordRequest(
                    user_id=uuid4(),
                    current_password="any",
                    new_password="NewPass@456",
                )
            )

    @pytest.mark.asyncio
    async def test_change_password_to_short_fails(self, repo, admin_user):
        """تغيير كلمة المرور لكلمة قصيرة يفشل."""
        create_uc = CreateUserUseCase(repo)
        user = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"short_new_{uuid4().hex[:8]}",
                password="OldPass@123",
                email=f"sn_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )

        uc = ChangePasswordUseCase(repo)
        with pytest.raises(ValidationException):
            await uc.execute(
                ChangePasswordRequest(
                    user_id=user.id,
                    current_password="OldPass@123",
                    new_password="short",
                )
            )


class TestResetPasswordUseCase:
    """اختبارات إعادة تعيين كلمة المرور (للمدير)."""

    @pytest.mark.asyncio
    async def test_reset_password_success(self, repo, admin_user):
        """المدير يُعيد تعيين كلمة مرور مستخدم."""
        create_uc = CreateUserUseCase(repo)
        user = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"reset_{uuid4().hex[:8]}",
                password="OldPass@123",
                email=f"reset_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )

        uc = ResetPasswordUseCase(repo)
        temp_password = await uc.execute(
            ResetPasswordRequest(
                target_user_id=user.id,
                admin_user_id=admin_user.id,
            ),
            admin=admin_user,
        )
        assert temp_password is not None
        assert len(temp_password) >= 8

        # Verify can login with temp password
        login_uc = LoginUseCase(repo)
        response = await login_uc.execute(
            LoginRequest(username=user.username, password=temp_password)
        )
        assert response.user.id == user.id

    @pytest.mark.asyncio
    async def test_reset_password_unlocks_account(self, repo, admin_user):
        """إعادة تعيين كلمة المرور تفتح الحساب المقفل."""
        create_uc = CreateUserUseCase(repo)
        user = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"locked_reset_{uuid4().hex[:8]}",
                password="Pass@123",
                email=f"lr_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )

        # Lock the account
        login_uc = LoginUseCase(repo)
        for _ in range(User.MAX_FAILED_ATTEMPTS):
            with pytest.raises(Exception):
                await login_uc.execute(
                    LoginRequest(username=user.username, password="wrong")
                )

        # Verify locked
        locked_user = await repo.get_by_id(user.id)
        assert locked_user.is_locked()

        # Reset password
        uc = ResetPasswordUseCase(repo)
        temp_pass = await uc.execute(
            ResetPasswordRequest(target_user_id=user.id, admin_user_id=admin_user.id),
            admin=admin_user,
        )

        # Verify unlocked
        reset_user = await repo.get_by_id(user.id)
        assert not reset_user.is_locked()
        assert reset_user.status == UserStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_reset_password_by_non_admin_fails(self, repo, admin_user):
        """محاسب لا يمكنه إعادة تعيين كلمات المرور."""
        create_uc = CreateUserUseCase(repo)
        target = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"target_{uuid4().hex[:8]}",
                password="Pass@123",
                email=f"target_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )
        accountant = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"acc_reset_{uuid4().hex[:8]}",
                password="Pass@123",
                email=f"ar_{uuid4().hex[:8]}@test.com",
                role=UserRole.ACCOUNTANT,
            ),
            current_user=admin_user,
        )

        uc = ResetPasswordUseCase(repo)
        with pytest.raises(PermissionDeniedException):
            await uc.execute(
                ResetPasswordRequest(target_user_id=target.id, admin_user_id=accountant.id),
                admin=accountant,
            )

    @pytest.mark.asyncio
    async def test_reset_password_nonexistent_user(self, repo, admin_user):
        """إعادة تعيين كلمة مرور لمستخدم غير موجود يفشل."""
        uc = ResetPasswordUseCase(repo)
        with pytest.raises(UserNotFoundException):
            await uc.execute(
                ResetPasswordRequest(target_user_id=uuid4(), admin_user_id=admin_user.id),
                admin=admin_user,
            )


class TestUnlockUserUseCase:
    """اختبارات فتح قفل المستخدم."""

    @pytest.mark.asyncio
    async def test_unlock_user_success(self, repo, admin_user):
        """فتح قفل مستخدم بنجاح."""
        create_uc = CreateUserUseCase(repo)
        user = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"unlock_{uuid4().hex[:8]}",
                password="Pass@123",
                email=f"ul_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )

        # Lock
        login_uc = LoginUseCase(repo)
        for _ in range(User.MAX_FAILED_ATTEMPTS):
            with pytest.raises(Exception):
                await login_uc.execute(
                    LoginRequest(username=user.username, password="wrong")
                )

        # Unlock
        uc = UnlockUserUseCase(repo)
        unlocked = await uc.execute(user.id, admin=admin_user)
        assert not unlocked.is_locked()
        assert unlocked.status == UserStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_unlock_by_non_admin_fails(self, repo, admin_user):
        """محاسب لا يمكنه فتح قفل الحسابات."""
        create_uc = CreateUserUseCase(repo)
        target = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"target_unlock_{uuid4().hex[:8]}",
                password="Pass@123",
                email=f"tu_{uuid4().hex[:8]}@test.com",
            ),
            current_user=admin_user,
        )
        accountant = await create_uc.execute(
            CreateUserRequest(
                full_name="Test User",
                username=f"acc_unlock_{uuid4().hex[:8]}",
                password="Pass@123",
                email=f"au_{uuid4().hex[:8]}@test.com",
                role=UserRole.ACCOUNTANT,
            ),
            current_user=admin_user,
        )

        uc = UnlockUserUseCase(repo)
        with pytest.raises(PermissionDeniedException):
            await uc.execute(target.id, admin=accountant)

    @pytest.mark.asyncio
    async def test_unlock_nonexistent_user(self, repo, admin_user):
        """فتح قفل مستخدم غير موجود يفشل."""
        uc = UnlockUserUseCase(repo)
        with pytest.raises(UserNotFoundException):
            await uc.execute(uuid4(), admin=admin_user)


class TestPasswordHasher:
    """اختبارات إضافية لـ PasswordHasher."""

    def test_verify_empty_password(self):
        """التحقق من كلمة مرور فارغة يُعيد False."""
        assert PasswordHasher.verify("", "somehash") is False

    def test_verify_empty_hash(self):
        """التحقق من hash فارغ يُعيد False."""
        assert PasswordHasher.verify("password", "") is False

    def test_verify_invalid_hash_format(self):
        """التحقق من hash غير صالح يُعيد False (لا يرمي استثناء)."""
        # Should not raise, just return False
        result = PasswordHasher.verify("password", "not-a-valid-hash")
        assert result is False

    def test_hash_with_special_characters(self):
        """تشفير كلمة مرور بحروف خاصة."""
        password = "P@$$w0rd!#%^&*()"
        hashed = PasswordHasher.hash(password)
        assert PasswordHasher.verify(password, hashed) is True

    def test_hash_with_arabic_characters(self):
        """تشفير كلمة مرور بالعربية."""
        password = "كلمةمرور@123"
        hashed = PasswordHasher.hash(password)
        assert PasswordHasher.verify(password, hashed) is True

    def test_hash_with_unicode(self) -> None:
        """تشفير كلمة مرور بحروف Unicode."""
        password = "密码密码@123456"
        hashed = PasswordHasher.hash(password)
        assert PasswordHasher.verify(password, hashed) is True
