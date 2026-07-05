"""
Unit of Work Pattern - حل مشكلة Atomicity

يضمن أن كل Use Case معقد (مثل إنشاء فاتورة) يُنفّذ في معاملة واحدة
(single database transaction). لو فشلت أي خطوة، تُلغى كل التغييرات.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

from infrastructure.db.session import get_engine
from sqlalchemy.orm import Session, sessionmaker


class UnitOfWork:
    """Unit of Work - يُدير معاملة واحدة قابلة للـ rollback.

    Usage:
        async with UnitOfWork() as uow:
            # كل العمليات هنا في معاملة واحدة
            customer_repo = SqlAlchemyCustomerRepository(uow.session)
            ...
        # exit: commit تلقائي (أو rollback عند الاستثناء)
    """

    _session: Optional[Session] = None

    def __init__(self) -> None:
        self._sessionmaker = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    def __enter__(self) -> "UnitOfWork":
        self._session = self._sessionmaker()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session is None:
            return
        try:
            if exc_type is not None:
                # Exception occurred - rollback
                self._session.rollback()
            else:
                # Success - commit
                self._session.commit()
        finally:
            self._session.close()
            self._session = None

    @property
    def session(self) -> Session:
        """الحصول على جلسة DB الحالية."""
        if self._session is None:
            raise RuntimeError("UnitOfWork not entered. Use 'async with UnitOfWork(): ...'")
        return self._session

    def commit(self) -> None:
        """Commit يدوي (نادرًا ما يُستخدم)."""
        if self._session:
            self._session.commit()

    def rollback(self) -> None:
        """Rollback يدوي."""
        if self._session:
            self._session.rollback()


@contextmanager
def atomic_transaction() -> Generator[Session, None, None]:
    """Context manager لمعاملة ذرية مباشرة.

    Usage:
        with atomic_transaction() as session:
            session.add(obj1)
            session.add(obj2)
        # commit تلقائي عند الخروج
    """
    session_factory = sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
