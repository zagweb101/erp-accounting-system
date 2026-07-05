"""
SQLAlchemy Account & Journal Repository Implementations
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from domain.entities.account import Account
from domain.entities.journal import JournalEntry, JournalEntryStatus, JournalLine
from domain.value_objects.value_objects import AccountCode, AccountType
from infrastructure.db.models.account_model import AccountModel
from infrastructure.db.models.journal_model import JournalEntryModel, JournalLineModel
from infrastructure.db.session import session_scope
from use_cases.repositories.interfaces import IAccountRepository, IJournalEntryRepository


# ============================================================
# Account Repository
# ============================================================
class SqlAlchemyAccountRepository(IAccountRepository):
    def _to_entity(self, m: AccountModel) -> Account:
        """ To Entity."""
        return Account(
            id=UUID(m.id),
            code=AccountCode(m.code),
            name=m.name,
            name_en=m.name_en,
            account_type=AccountType(m.account_type),
            parent_id=UUID(m.parent_id) if m.parent_id else None,
            is_active=m.is_active,
            is_posting_account=m.is_posting_account,
            description=m.description,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def get_by_id(self, account_id: UUID) -> Optional[Account]:
        with session_scope() as session:
            m = session.execute(
                select(AccountModel).where(AccountModel.id == str(account_id))
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def get_by_code(self, code: str) -> Optional[Account]:
        with session_scope() as session:
            m = session.execute(
                select(AccountModel).where(AccountModel.code == code)
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def save(self, account: Account) -> Account:
        with session_scope() as session:
            existing = session.execute(
                select(AccountModel).where(AccountModel.id == str(account.id))
            ).scalar_one_or_none()
            if existing is None:
                m = AccountModel(
                    id=str(account.id),
                    code=str(account.code),
                    name=account.name,
                    name_en=account.name_en,
                    account_type=account.account_type.value,
                    parent_id=str(account.parent_id) if account.parent_id else None,
                    is_active=account.is_active,
                    is_posting_account=account.is_posting_account,
                    description=account.description,
                )
            else:
                m = existing
                m.code = str(account.code)
                m.name = account.name
                m.name_en = account.name_en
                m.account_type = account.account_type.value
                m.parent_id = str(account.parent_id) if account.parent_id else None
                m.is_active = account.is_active
                m.is_posting_account = account.is_posting_account
                m.description = account.description
            session.add(m)
            session.flush()
            session.refresh(m)
            return self._to_entity(m)

    async def list_by_type(self, account_type: str) -> list[Account]:
        with session_scope() as session:
            stmt = (
                select(AccountModel)
                .where(AccountModel.account_type == account_type)
                .order_by(AccountModel.code)
            )
            models = session.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]

    async def list_children(self, parent_id: UUID) -> list[Account]:
        with session_scope() as session:
            stmt = (
                select(AccountModel)
                .where(AccountModel.parent_id == str(parent_id))
                .order_by(AccountModel.code)
            )
            models = session.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]

    async def get_account_balance(self, account_id: UUID) -> float:
        """حساب الرصيد من القيود المرحَّلة."""
        with session_scope() as session:
            stmt = select(
                func.coalesce(func.sum(JournalLineModel.debit), 0).label("total_debit"),
                func.coalesce(func.sum(JournalLineModel.credit), 0).label("total_credit"),
            ).join(
                JournalEntryModel, JournalLineModel.entry_id == JournalEntryModel.id
            ).where(
                and_(
                    JournalLineModel.account_id == str(account_id),
                    JournalEntryModel.status == JournalEntryStatus.POSTED.value,
                )
            )
            result = session.execute(stmt).one()
            return float(result.total_debit - result.total_credit)


# ============================================================
# Journal Entry Repository
# ============================================================
class SqlAlchemyJournalEntryRepository(IJournalEntryRepository):
    def _to_entity(self, m: JournalEntryModel, include_lines: bool = True) -> JournalEntry:
        # Normalize reference_type: it's stored as string in DB
        from domain.entities.journal import JournalEntryReferenceType
        ref_type = m.reference_type
        if isinstance(ref_type, str):
            try:
                ref_type = JournalEntryReferenceType(ref_type)
            except ValueError:
                ref_type = JournalEntryReferenceType.MANUAL

        entry = JournalEntry(
            id=UUID(m.id),
            entry_no=m.entry_no,
            date=m.date,
            reference_type=ref_type,
            reference_id=UUID(m.reference_id) if m.reference_id else None,
            description=m.description,
            status=JournalEntryStatus(m.status),
            created_by=UUID(m.created_by),
            posted_by=UUID(m.posted_by) if m.posted_by else None,
            posted_at=m.posted_at,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        if include_lines and m.lines:
            for lm in m.lines:
                line = JournalLine(
                    id=UUID(lm.id),
                    entry_id=entry.id,
                    account_id=UUID(lm.account_id),
                    debit=Decimal(str(lm.debit)),
                    credit=Decimal(str(lm.credit)),
                    description=lm.description,
                    created_at=lm.created_at,
                )
                entry.lines.append(line)
        return entry

    async def get_by_id(self, entry_id: UUID) -> Optional[JournalEntry]:
        with session_scope() as session:
            m = session.execute(
                select(JournalEntryModel).where(JournalEntryModel.id == str(entry_id))
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def get_by_no(self, entry_no: str) -> Optional[JournalEntry]:
        with session_scope() as session:
            m = session.execute(
                select(JournalEntryModel).where(JournalEntryModel.entry_no == entry_no)
            ).scalar_one_or_none()
            return self._to_entity(m) if m else None

    async def save(self, entry: JournalEntry) -> JournalEntry:
        with session_scope() as session:
            existing = session.execute(
                select(JournalEntryModel).where(JournalEntryModel.id == str(entry.id))
            ).scalar_one_or_none()
            # Normalize enums to .value (handles both Enum instances and strings)
            ref_type_val = entry.reference_type.value if hasattr(entry.reference_type, "value") else str(entry.reference_type)
            status_val = entry.status.value if hasattr(entry.status, "value") else str(entry.status)

            if existing is None:
                m = JournalEntryModel(
                    id=str(entry.id),
                    entry_no=entry.entry_no,
                    date=entry.date,
                    reference_type=ref_type_val,
                    reference_id=str(entry.reference_id) if entry.reference_id else None,
                    description=entry.description,
                    status=status_val,
                    created_by=str(entry.created_by),
                    posted_by=str(entry.posted_by) if entry.posted_by else None,
                    posted_at=entry.posted_at,
                )
            else:
                m = existing
                m.entry_no = entry.entry_no
                m.date = entry.date
                m.reference_type = ref_type_val
                m.reference_id = str(entry.reference_id) if entry.reference_id else None
                m.description = entry.description
                m.status = status_val
                m.posted_by = str(entry.posted_by) if entry.posted_by else None
                m.posted_at = entry.posted_at

            # Sync lines (delete existing, add new)
            if existing is not None:
                for old_line in list(m.lines):
                    session.delete(old_line)
                m.lines = []

            for line in entry.lines:
                lm = JournalLineModel(
                    id=str(line.id),
                    entry_id=m.id,
                    account_id=str(line.account_id),
                    debit=line.debit,
                    credit=line.credit,
                    description=line.description,
                )
                m.lines.append(lm)

            session.add(m)
            session.flush()
            session.refresh(m)
            return self._to_entity(m)

    async def list_by_date_range(
        self, start_date, end_date, skip: int = 0, limit: int = 100
    ) -> list[JournalEntry]:
        with session_scope() as session:
            stmt = (
                select(JournalEntryModel)
                .where(
                    and_(
                        JournalEntryModel.date >= start_date,
                        JournalEntryModel.date <= end_date,
                    )
                )
                .order_by(JournalEntryModel.date.desc())
                .offset(skip)
                .limit(limit)
            )
            models = session.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]

    async def list_by_account(
        self, account_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[JournalEntry]:
        with session_scope() as session:
            stmt = (
                select(JournalEntryModel)
                .join(JournalLineModel, JournalLineModel.entry_id == JournalEntryModel.id)
                .where(JournalLineModel.account_id == str(account_id))
                .order_by(JournalEntryModel.date.desc())
                .offset(skip)
                .limit(limit)
                .distinct()
            )
            models = session.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]


    async def _save_in_session(self, entry: JournalEntry, session) -> JournalEntry:
        """حفظ القيد في session موجودة (للـ UnitOfWork)."""
        existing = session.execute(
            select(JournalEntryModel).where(JournalEntryModel.id == str(entry.id))
        ).scalar_one_or_none()

        ref_type_val = entry.reference_type.value if hasattr(entry.reference_type, "value") else str(entry.reference_type)
        status_val = entry.status.value if hasattr(entry.status, "value") else str(entry.status)

        if existing is None:
            m = JournalEntryModel(
                id=str(entry.id),
                entry_no=entry.entry_no,
                date=entry.date,
                reference_type=ref_type_val,
                reference_id=str(entry.reference_id) if entry.reference_id else None,
                description=entry.description,
                status=status_val,
                created_by=str(entry.created_by),
                posted_by=str(entry.posted_by) if entry.posted_by else None,
                posted_at=entry.posted_at,
            )
        else:
            m = existing
            m.entry_no = entry.entry_no
            m.date = entry.date
            m.reference_type = ref_type_val
            m.reference_id = str(entry.reference_id) if entry.reference_id else None
            m.description = entry.description
            m.status = status_val
            m.posted_by = str(entry.posted_by) if entry.posted_by else None
            m.posted_at = entry.posted_at

        if existing is not None:
            for old_line in list(m.lines):
                session.delete(old_line)
            m.lines = []

        for line in entry.lines:
            lm = JournalLineModel(
                id=str(line.id),
                entry_id=m.id,
                account_id=str(line.account_id),
                debit=line.debit,
                credit=line.credit,
                description=line.description,
            )
            m.lines.append(lm)

        session.add(m)
        session.flush()
        session.refresh(m)
        return self._to_entity(m)

    async def next_entry_no(self) -> str:
        """توليد رقم قيد تسلسلي: JE-YYYY-NNNNNN."""
        with session_scope() as session:
            year = datetime.now().year
            prefix = f"JE-{year}-"
            stmt = select(func.count(JournalEntryModel.id)).where(
                JournalEntryModel.entry_no.like(f"{prefix}%")
            )
            count = session.execute(stmt).scalar() or 0
            return f"{prefix}{count + 1:06d}"
