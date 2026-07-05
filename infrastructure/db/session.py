"""
Database Session & Engine Setup

SQLAlchemy 2.0 sync engine with session factory.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from infrastructure.config.settings import get_settings


# Engine (lazy initialized)
_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None
Base = declarative_base()


def get_engine() -> Engine:
    """الحصول على محرك قاعدة البيانات (singleton).

    يقرأ الإعدادات من get_settings() في كل مرة (لا cache) — يسمح بتغيير
    DATABASE_URL أثناء الاختبارات.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False}
            if "sqlite" in settings.DATABASE_URL
            else {},
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """الحصول على مصنع الجلسات (singleton)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_session() -> Session:
    """الحصول على جلسة قاعدة بيانات جديدة."""
    return get_session_factory()()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager لجلسة DB مع commit/rollback تلقائي.

    Usage:
        with session_scope() as session:
            session.add(obj)
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """تهيئة قاعدة البيانات: إنشاء كل الجداول."""
    # استيراد كل الـ models لتسجيلها في Base.metadata
    from infrastructure.db.models import (
        account_model,
        inventory_model,
        invoice_model,
        journal_model,
        party_model,
        product_model,
        user_model,
    )

    Base.metadata.create_all(bind=get_engine())


def drop_db() -> None:
    """حذف كل الجداول (للتطوير فقط!)."""
    from infrastructure.db.models import (
        account_model,
        inventory_model,
        invoice_model,
        journal_model,
        party_model,
        product_model,
        user_model,
    )

    Base.metadata.drop_all(bind=get_engine())
