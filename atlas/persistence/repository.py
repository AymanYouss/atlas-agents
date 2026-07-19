"""Repository interface plus an in-memory implementation.

The API and services depend only on :class:`RunRepository`. Postgres is the
production backend (:mod:`atlas.persistence.sql`); the in-memory implementation
backs tests and single-process local runs.
"""

from __future__ import annotations

import abc
from collections import defaultdict

from atlas.persistence.records import EventRecord, RunRecord
from atlas.schemas.run import RunStatus


class RunRepository(abc.ABC):
    @abc.abstractmethod
    async def create(self, record: RunRecord) -> RunRecord: ...

    @abc.abstractmethod
    async def get(self, run_id: str) -> RunRecord | None: ...

    @abc.abstractmethod
    async def update(self, record: RunRecord) -> RunRecord: ...

    @abc.abstractmethod
    async def list_runs(self, *, limit: int = 50, offset: int = 0) -> list[RunRecord]: ...

    @abc.abstractmethod
    async def append_event(self, event: EventRecord) -> None: ...

    @abc.abstractmethod
    async def list_events(self, run_id: str, *, after_seq: int = 0) -> list[EventRecord]: ...

    async def set_status(self, run_id: str, status: RunStatus) -> None:
        record = await self.get(run_id)
        if record:
            record.status = status
            record.touch()
            await self.update(record)


class InMemoryRunRepository(RunRepository):
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._events: dict[str, list[EventRecord]] = defaultdict(list)

    async def create(self, record: RunRecord) -> RunRecord:
        self._runs[record.id] = record.model_copy(deep=True)
        return record

    async def get(self, run_id: str) -> RunRecord | None:
        rec = self._runs.get(run_id)
        return rec.model_copy(deep=True) if rec else None

    async def update(self, record: RunRecord) -> RunRecord:
        record.touch()
        self._runs[record.id] = record.model_copy(deep=True)
        return record

    async def list_runs(self, *, limit: int = 50, offset: int = 0) -> list[RunRecord]:
        ordered = sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)
        return [r.model_copy(deep=True) for r in ordered[offset : offset + limit]]

    async def append_event(self, event: EventRecord) -> None:
        self._events[event.run_id].append(event)

    async def list_events(self, run_id: str, *, after_seq: int = 0) -> list[EventRecord]:
        return [e for e in self._events[run_id] if e.seq > after_seq]
