"""Domain records persisted for each run.

These are storage-agnostic Pydantic models. Both the Postgres-backed repository
and the in-memory repository read and write these, so the API and service layers
never depend on SQLAlchemy directly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from atlas.schemas.run import RunStatus


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RunRecord(BaseModel):
    id: str
    goal: str
    status: RunStatus = RunStatus.PENDING
    config: dict[str, Any] = Field(default_factory=dict)
    plan: dict[str, Any] | None = None
    results: dict[str, Any] = Field(default_factory=dict)
    critiques: list[dict[str, Any]] = Field(default_factory=list)
    report: dict[str, Any] | None = None
    approvals: dict[str, Any] = Field(default_factory=dict)
    pending_approvals: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()


class EventRecord(BaseModel):
    run_id: str
    seq: int
    type: str
    step_id: str | None = None
    agent: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: datetime = Field(default_factory=_utcnow)
