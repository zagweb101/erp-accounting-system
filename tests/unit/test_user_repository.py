"""
اختبارات شاملة لـ UserRepository (رفع التغطية من 32% إلى 80%+)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


from infrastructure.db.models.user_model import UserModel

from adapters.repositories.sql_alchemy.user_repository import SqlAlchemyUserRepository
from domain.entities.user import User, UserStatus
from domain.value_objects.value_objects import UserRole
from use_cases.auth.auth_use_cases import PasswordHasher


@pytest.fixture
def repo():
    return SqlAlchemyUserRepository()


@pytest.fixture
def sample_user_data():
    """بيانات مستخدم للاختبار."""
    return {
        "id": uuid4(),
        "username": f"testuser_{uuid4().hex[:8]}",
        "email": f"test_{uuid4().hex[:8]}@example.com",
        "password_hash": PasswordHasher.hash("TestPassword@123"),
        "full_name": "Test User",
        "role": UserRole.ACCOUNTANT,
        "status": UserStatus.ACTIVE,
    }


class TestUserRepositoryCreate:
    """اختبارات إنشاء المستخدمين."""

    @pytest.mark.asyncio
    async def test_save_new_user(self, repo, sample_user_data):
        """حفظ مستخدم جديد ينجح."""
        user = User(**sample_user_data)
        saved = await repo.save(user)
        assert saved.id == user.id
        assert saved.username == user.username
        assert saved.email == user.email
        assert saved.role == UserRole.ACCOUNTANT

    @pytest.mark.asyncio
    async def test_save_existing_user_updates(self, repo, sample_user_data):
        """حفظ مستخدم موجود يُحدّثه."""
        user = User(**sample_user_data)
        await repo.save(user)

        # Modify and save again
        user.full_name = "Updated Name"
        user.email = f"updated_{uuid4().hex[:8]}@example.com"
        updated = await repo.save(user)

        assert updated.full_name == "Updated Name"
        assert updated.email == user.email

    @pytest.mark.asyncio
    async def test_save_user_with_all_roles(self, repo):
        """حفظ مستخدمين بكل الأدوار."""
        for role in UserRole:
            user = User(
                id=uuid4(),
                username=f"role_test_{role.value}_{uuid4().hex[:8]}",
                email=f"role_{role.value}_{uuid4().hex[:8]}@test.com",
                password_hash=PasswordHasher.hash("Password@123"),
                full_name=f"Test {role.value}",
                role=role,
                status=UserStatus.ACTIVE,
            )
            saved = await repo.save(user)
            assert saved.role == role


class TestUserRepositoryRead:
    """اختبارات قراءة المستخدمين."""

    @pytest.mark.asyncio
    async def test_get_by_id_existing(self, repo, sample_user_data):
        """get_by_id لمستخدم موجود ينجح."""
        user = User(**sample_user_data)
        await repo.save(user)

        fetched = await repo.get_by_id(user.id)
        assert fetched is not None
        assert fetched.id == user.id
        assert fetched.username == user.username

    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent(self, repo):
        """get_by_id لمستخدم غير موجود يُعيد None."""
        result = await repo.get_by_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_username_existing(self, repo, sample_user_data):
        """get_by_username لمستخدم موجود ينجح."""
        user = User(**sample_user_data)
        await repo.save(user)

        fetched = await repo.get_by_username(user.username)
        assert fetched is not None
        assert fetched.username == user.username

    @pytest.mark.asyncio
    async def test_get_by_username_nonexistent(self, repo):
        """get_by_username لمستخدم غير موجود يُعيد None."""
        result = await repo.get_by_username("nonexistent_user_xyz")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_username_preserves_password_hash(self, repo, sample_user_data):
        """get_by_username يحفظ password_hash بشكل صحيح."""
        user = User(**sample_user_data)
        await repo.save(user)

        fetched = await repo.get_by_username(user.username)
        assert fetched.password_hash == user.password_hash
        # Verify it's a valid bcrypt hash
        assert PasswordHasher.verify("TestPassword@123", fetched.password_hash)

    @pytest.mark.asyncio
    async def test_get_by_id_preserves_all_fields(self, repo, sample_user_data):
        """get_by_id يحفظ كل الحقول."""
        user = User(**sample_user_data)
        user.failed_login_attempts = 3
        await repo.save(user)

        fetched = await repo.get_by_id(user.id)
        assert fetched.failed_login_attempts == 3
        assert fetched.full_name == user.full_name
        assert fetched.role == user.role
        assert fetched.status == user.status

    @pytest.mark.asyncio
    async def test_list_all_returns_list(self, repo):
        """list_all يُعيد قائمة."""
        users = await repo.list_all(skip=0, limit=10)
        assert isinstance(users, list)
        assert len(users) >= 1  # at least admin

    @pytest.mark.asyncio
    async def test_list_all_pagination(self, repo):
        """list_all يحترم skip و limit."""
        # Create 5 users
        for i in range(5):
            user = User(
                id=uuid4(),
                username=f"page_test_{i}_{uuid4().hex[:8]}",
                email=f"page_{i}_{uuid4().hex[:8]}@test.com",
                password_hash=PasswordHasher.hash("Password@123"),
                full_name=f"User {i}",
                role=UserRole.ACCOUNTANT,
                status=UserStatus.ACTIVE,
            )
            await repo.save(user)

        # Get first 3
        first_page = await repo.list_all(skip=0, limit=3)
        assert len(first_page) <= 3

        # Get next 3
        second_page = await repo.list_all(skip=3, limit=3)
        assert len(second_page) <= 3

        # Pages should not overlap (different IDs)
        first_ids = {u.id for u in first_page}
        second_ids = {u.id for u in second_page}
        assert first_ids.isdisjoint(second_ids)

    @pytest.mark.asyncio
    async def test_list_all_returns_domain_entities(self, repo):
        """list_all يُعيد Domain entities وليس ORM models."""
        users = await repo.list_all()
        for u in users:
            assert isinstance(u, User)
            assert hasattr(u, "has_permission")  # Domain method
            assert hasattr(u, "is_locked")  # Domain method


class TestUserRepositoryDelete:
    """اختبارات حذف المستخدمين."""

    @pytest.mark.asyncio
    async def test_delete_existing_user(self, repo, sample_user_data):
        """حذف مستخدم موجود ينجح."""
        user = User(**sample_user_data)
        await repo.save(user)

        result = await repo.delete(user.id)
        assert result is True

        # Verify deleted
        fetched = await repo.get_by_id(user.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, repo):
        """حذف مستخدم غير موجود يُعيد False."""
        result = await repo.delete(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_user_then_recreate(self, repo):
        """حذف ثم إعادة إنشاء مستخدم بنفس الاسم ينجح."""
        user = User(
            id=uuid4(),
            username=f"recycle_{uuid4().hex[:8]}",
            email=f"recycle_{uuid4().hex[:8]}@test.com",
            password_hash=PasswordHasher.hash("Password@123"),
            full_name="Recycle Test",
        )
        await repo.save(user)
        await repo.delete(user.id)

        # Recreate with same username
        new_user = User(
            id=uuid4(),
            username=user.username,
            email=user.email,
            password_hash=PasswordHasher.hash("Password@123"),
            full_name="Recycled User",
        )
        saved = await repo.save(new_user)
        assert saved.id != user.id
        assert saved.username == user.username


class TestUserRepositoryUpdate:
    """اختبارات تحديث المستخدمين."""

    @pytest.mark.asyncio
    async def test_update_role(self, repo, sample_user_data):
        """تحديث دور المستخدم."""
        user = User(**sample_user_data)
        await repo.save(user)

        user.role = UserRole.FINANCIAL_MANAGER
        updated = await repo.save(user)
        assert updated.role == UserRole.FINANCIAL_MANAGER

    @pytest.mark.asyncio
    async def test_update_status(self, repo, sample_user_data):
        """تحديث حالة المستخدم."""
        user = User(**sample_user_data)
        await repo.save(user)

        user.disable()
        updated = await repo.save(user)
        assert updated.status == UserStatus.DISABLED
        assert not updated.is_active()

    @pytest.mark.asyncio
    async def test_update_failed_login_attempts(self, repo, sample_user_data):
        """تحديث عداد المحاولات الفاشلة."""
        user = User(**sample_user_data)
        await repo.save(user)

        user.record_failed_login()
        user.record_failed_login()
        updated = await repo.save(user)
        assert updated.failed_login_attempts == 2

    @pytest.mark.asyncio
    async def test_update_lock_user(self, repo, sample_user_data):
        """قفل المستخدم بعد 5 محاولات."""
        user = User(**sample_user_data)
        await repo.save(user)

        for _ in range(User.MAX_FAILED_ATTEMPTS):
            user.record_failed_login()
        updated = await repo.save(user)

        assert updated.is_locked()
        assert updated.status == UserStatus.LOCKED

    @pytest.mark.asyncio
    async def test_unlock_user(self, repo, sample_user_data):
        """فتح قفل المستخدم."""
        user = User(**sample_user_data)
        for _ in range(User.MAX_FAILED_ATTEMPTS):
            user.record_failed_login()
        await repo.save(user)

        user.unlock()
        updated = await repo.save(user)
        assert not updated.is_locked()
        assert updated.status == UserStatus.ACTIVE
        assert updated.failed_login_attempts == 0

    @pytest.mark.asyncio
    async def test_successful_login_resets_counters(self, repo, sample_user_data):
        """تسجيل دخول ناجح يصفّر العدادات."""
        user = User(**sample_user_data)
        user.record_failed_login()
        user.record_failed_login()
        await repo.save(user)

        user.record_successful_login()
        updated = await repo.save(user)
        assert updated.failed_login_attempts == 0
        assert updated.last_login_at is not None

    @pytest.mark.asyncio
    async def test_update_password_hash(self, repo, sample_user_data):
        """تحديث كلمة المرور."""
        user = User(**sample_user_data)
        await repo.save(user)

        new_hash = PasswordHasher.hash("NewPassword@456")
        user.password_hash = new_hash
        updated = await repo.save(user)
        assert updated.password_hash == new_hash
        assert PasswordHasher.verify("NewPassword@456", updated.password_hash)


class TestUserRepositoryEdgeCases:
    """اختبارات الحالات الحدية."""

    @pytest.mark.asyncio
    async def test_user_with_special_chars_in_username(self, repo):
        """اسم مستخدم بحروف خاصة مسموح (_) و(.)."""
        user = User(
            id=uuid4(),
            username=f"user.name_{uuid4().hex[:8]}",
            email=f"special_{uuid4().hex[:8]}@test.com",
            password_hash=PasswordHasher.hash("Password@123"),
            full_name="Special User",
        )
        saved = await repo.save(user)
        fetched = await repo.get_by_username(saved.username)
        assert fetched is not None

    @pytest.mark.asyncio
    async def test_user_with_long_email(self, repo):
        """بريد إلكتروني طويل."""
        long_email = f"{'a' * 100}@example.com"
        user = User(
            id=uuid4(),
            username=f"longmail_{uuid4().hex[:8]}",
            email=long_email,
            password_hash=PasswordHasher.hash("Password@123"),
        )
        saved = await repo.save(user)
        assert saved.email == long_email

    @pytest.mark.asyncio
    async def test_multiple_users_different_ids_same_username_fails(self, repo):
        """لا يمكن وجود مستخدمين بنفس اسم المستخدم (unique constraint)."""
        username = f"duplicate_{uuid4().hex[:8]}"
        user1 = User(
            id=uuid4(), username=username, email=f"u1_{uuid4().hex[:8]}@test.com",
            password_hash=PasswordHasher.hash("Password@123"),
        )
        await repo.save(user1)

        user2 = User(
            id=uuid4(), username=username, email=f"u2_{uuid4().hex[:8]}@test.com",
            password_hash=PasswordHasher.hash("Password@123"),
        )
        # Should raise (unique constraint)
        with pytest.raises(Exception):
            await repo.save(user2)
