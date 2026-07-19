"""Postgres-backed repository implementation."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from atlas.persistence.db import Base
from atlas.persistence.records import EventRecord, RunRecord
from atlas.persistence.repository import RunRepository
from atlas.schemas.run import RunStatus


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    results: Mapped[dict] = mapped_column(JSONB, default=dict)
    critiques: Mapped[list] = mapped_column(JSONB, default=list)
    report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    approvals: Mapped[dict] = mapped_column(JSONB, default=dict)
    pending_approvals: Mapped[list] = mapped_column(JSONB, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventRow(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer, index=True)
    type: Mapped[str] = mapped_column(String(48))
    step_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _to_record(row: RunRow) -> RunRecord:
    return RunRecord(
        id=row.id,
        goal=row.goal,
        status=RunStatus(row.status),
        config=row.config or {},
        plan=row.plan,
        results=row.results or {},
        critiques=row.critiques or [],
        report=row.report,
        approvals=row.approvals or {},
        pending_approvals=row.pending_approvals or [],
        error=row.error,
        tags=row.tags or [],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _apply(row: RunRow, rec: RunRecord) -> None:
    row.goal = rec.goal
    row.status = rec.status
    row.config = rec.config
    row.plan = rec.plan
    row.results = rec.results
    row.critiques = rec.critiques
    row.report = rec.report
    row.approvals = rec.approvals
    row.pending_approvals = rec.pending_approvals
    row.error = rec.error
    row.tags = rec.tags
    row.created_at = rec.created_at
    row.updated_at = rec.updated_at


class SqlAlchemyRunRepository(RunRepository):
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def create(self, record: RunRecord) -> RunRecord:
        async with self._sessions() as s, s.begin():
            row = RunRow(id=record.id)
            _apply(row, record)
            s.add(row)
        return record

    async def get(self, run_id: str) -> RunRecord | None:
        async with self._sessions() as s:
            row = await s.get(RunRow, run_id)
            return _to_record(row) if row else None

    async def update(self, record: RunRecord) -> RunRecord:
        record.touch()
        async with self._sessions() as s, s.begin():
            row = await s.get(RunRow, record.id)
            if row is None:
                row = RunRow(id=record.id)
                s.add(row)
            _apply(row, record)
        return record

    async def list_runs(self, *, limit: int = 50, offset: int = 0) -> list[RunRecord]:
        async with self._sessions() as s:
            stmt = select(RunRow).order_by(RunRow.created_at.desc()).limit(limit).offset(offset)
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_record(r) for r in rows]

    async def append_event(self, event: EventRecord) -> None:
        async with self._sessions() as s, s.begin():
            s.add(
                EventRow(
                    run_id=event.run_id,
                    seq=event.seq,
                    type=event.type,
                    step_id=event.step_id,
                    agent=event.agent,
                    payload=event.payload,
                    ts=event.ts,
                )
            )

    async def list_events(self, run_id: str, *, after_seq: int = 0) -> list[EventRecord]:
        async with self._sessions() as s:
            stmt = (
                select(EventRow)
                .where(EventRow.run_id == run_id, EventRow.seq > after_seq)
                .order_by(EventRow.seq.asc())
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [
                EventRecord(
                    run_id=r.run_id,
                    seq=r.seq,
                    type=r.type,
                    step_id=r.step_id,
                    agent=r.agent,
                    payload=r.payload,
                    ts=r.ts,
                )
                for r in rows
            ]
