"""The checkpointed graph state.

Everything here is JSON-serializable so LangGraph can persist it to Postgres and
resume a run in a fresh process. Non-serializable per-run objects (LLM clients,
the tool registry, the budget) live in :mod:`atlas.graph.context`, keyed by
``run_id``, and are rebuilt by the orchestrator on resume.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AtlasState(TypedDict, total=False):
    run_id: str
    goal: str
    # Serialized Plan for the current (possibly replanned) iteration.
    plan: dict[str, Any] | None
    # Step ids completed within the current plan iteration.
    completed: list[str]
    # Step ids that failed within the current plan iteration.
    failed: list[str]
    # All StepResults accumulated across iterations, keyed by unique step id.
    results: dict[str, dict[str, Any]]
    # All critiques produced, in order.
    critiques: list[dict[str, Any]]
    # Serialized final Report.
    report: dict[str, Any] | None
    status: str
    error: str | None
    replans: int
    # Resolved approval decisions, keyed by step id.
    approvals: dict[str, dict[str, Any]]
