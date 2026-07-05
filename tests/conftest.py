"""
Pytest configuration & fixtures

كل ملف اختبار يستخدم DB منفصل لتجنب التداخل.
"""
from __future__ import annotations

import os
import sys
import uuid as uuid_module
from pathlib import Path

import pytest

# Add project root to sys.path so we can import erp_accounting package
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def isolated_test_db(tmp_path, monkeypatch):
    """كل اختبار يستخدم DB منفصل في tmp_path.

    هذا يمنع التداخل بين الاختبارات ويضمن عزلًا كاملًا.
    """
    # Generate unique DB file per test
    db_file = tmp_path / f"test_{uuid_module.uuid4().hex[:8]}.db"
    db_url = f"sqlite:///{db_file}"

    # Set environment variable
    monkeypatch.setenv("DATABASE_URL", db_url)

    # Reset settings cache
    from infrastructure.config import settings as settings_module
    settings_module.settings = settings_module.Settings()
    settings_module.get_settings.cache_clear()

    # Reset DB engine/session factory
    from infrastructure.db import session as session_module
    session_module._engine = None
    session_module._SessionLocal = None

    # Initialize DB (lazy: only if needed by the test)
    # We use a marker to detect if init_db was called
    try:
        from infrastructure.db.session import init_db
        init_db()

        # Seed default data (admin user + chart of accounts)
        from infrastructure.db.seed import seed_admin_user, seed_chart_of_accounts
        seed_admin_user()
        seed_chart_of_accounts()
    except Exception as e:
        # Some tests (value_objects) don't need DB - ignore errors
        pass

    yield

    # Cleanup
    try:
        from infrastructure.db.session import get_engine
        engine = get_engine()
        engine.dispose()
    except Exception:
        pass


@pytest.fixture
def test_user_id():
    """UUID لمستخدم اختبار."""
    from uuid import uuid4
    return uuid4()


@pytest.fixture
def test_account_id():
    """UUID لحساب اختبار."""
    from uuid import uuid4
    return uuid4()
