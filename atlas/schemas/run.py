"""Runtime models: tool invocations, step results, critiques and approvals."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RunStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    AWAITING_APPROVAL = "awaiting_approval"
    CRITIQUING = "critiquing"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}


class RunConfig(BaseModel):
    """Per-run overrides layered on top of the global settings."""

    max_steps: int | None = None
    max_retries_per_step: int | None = None
    require_approval_for_tools: list[str] = Field(default_factory=list)
    auto_approve: bool = Field(
        default=False,
        description="If true, approval gates resolve automatically (used in evals/CI).",
    )
    tags: list[str] = Field(default_factory=list)


class ToolInvocation(BaseModel):
    """A single tool call made by an executor agent, with its result."""

    tool: str
    server: str = Field(default="", description="MCP server that owns the tool.")
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    ok: bool = True
    error: str | None = None
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: datetime | None = None
    duration_ms: int | None = None
    blocked_by_guardrail: str | None = Field(
        default=None,
        description="Set when a guardrail (e.g. injection scan) blocked the call.",
    )


class StepResult(BaseModel):
    """The outcome of executing one plan step."""

    step_id: str
    attempt: int = 1
    output: str = ""
    tool_invocations: list[ToolInvocation] = Field(default_factory=list)
    citations: list[str] = Field(
        default_factory=list, description="Citation markers surfaced by this step."
    )
    tokens_used: int = 0
    succeeded: bool = True
    error: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class Critique(BaseModel):
    """The critic's verdict on a step or on the final report."""

    target: str = Field(description="Step id under review, or 'report' for the final answer.")
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(
        default_factory=list, description="Concrete guidance for the retry, if any."
    )
    retry_recommended: bool = False


class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"


class ApprovalRequest(BaseModel):
    """A human-in-the-loop gate raised before a sensitive step runs."""

    id: str
    step_id: str
    reason: str
    proposed_action: str
    decision: ApprovalDecision = ApprovalDecision.PENDING
    decided_by: str | None = None
    note: str | None = None
    edited_instruction: str | None = Field(
        default=None,
        description="When decision is EDITED, the replacement instruction to run.",
    )
    created_at: datetime = Field(default_factory=_utcnow)
    decided_at: datetime | None = None
