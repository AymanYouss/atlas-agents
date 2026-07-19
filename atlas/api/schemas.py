"""Request/response models for the HTTP API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from atlas.persistence.records import RunRecord
from atlas.schemas.run import RunStatus


class CreateRunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)
    auto_approve: bool = False
    max_steps: int | None = Field(default=None, ge=1, le=100)
    tags: list[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    id: str
    goal: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_record(cls, r: RunRecord) -> RunSummary:
        return cls(
            id=r.id,
            goal=r.goal,
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at,
            tags=r.tags,
        )


class RunDetail(RunSummary):
    plan: dict[str, Any] | None = None
    results: dict[str, Any] = Field(default_factory=dict)
    critiques: list[dict[str, Any]] = Field(default_factory=list)
    report: dict[str, Any] | None = None
    pending_approvals: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None

    @classmethod
    def from_record(cls, r: RunRecord) -> RunDetail:
        return cls(
            id=r.id,
            goal=r.goal,
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at,
            tags=r.tags,
            plan=r.plan,
            results=r.results,
            critiques=r.critiques,
            report=r.report,
            pending_approvals=r.pending_approvals,
            error=r.error,
        )


class ApprovalDecisionBody(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|edited)$")
    note: str | None = None
    edited_instruction: str | None = None


class SubmitApprovalsRequest(BaseModel):
    # Keyed by step id.
    decisions: dict[str, ApprovalDecisionBody]


class RunListResponse(BaseModel):
    runs: list[RunSummary]
    limit: int
    offset: int
