"""Aggregation of task outcomes into a suite-level report."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from atlas.eval.scorer import ScoreBreakdown


class TaskOutcome(BaseModel):
    task_id: str
    category: str
    difficulty: str
    passed: bool
    score: float
    breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    steps: int = 0
    tokens: int = 0
    latency_ms: int = 0
    citations: int = 0
    blocked_injections: int = 0
    error: str | None = None
    notes: list[str] = Field(default_factory=list)


class GroupStat(BaseModel):
    total: int
    passed: int

    @property
    def success_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


class SuiteReport(BaseModel):
    suite: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    outcomes: list[TaskOutcome] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def passed(self) -> int:
        return sum(1 for o in self.outcomes if o.passed)

    @property
    def success_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def mean_score(self) -> float:
        return sum(o.score for o in self.outcomes) / self.total if self.total else 0.0

    @property
    def mean_tokens(self) -> float:
        return sum(o.tokens for o in self.outcomes) / self.total if self.total else 0.0

    @property
    def mean_latency_ms(self) -> float:
        return sum(o.latency_ms for o in self.outcomes) / self.total if self.total else 0.0

    @property
    def blocked_injections(self) -> int:
        return sum(o.blocked_injections for o in self.outcomes)

    def by_category(self) -> dict[str, GroupStat]:
        groups: dict[str, list[TaskOutcome]] = defaultdict(list)
        for o in self.outcomes:
            groups[o.category].append(o)
        return {
            cat: GroupStat(total=len(items), passed=sum(1 for i in items if i.passed))
            for cat, items in groups.items()
        }

    def by_difficulty(self) -> dict[str, GroupStat]:
        groups: dict[str, list[TaskOutcome]] = defaultdict(list)
        for o in self.outcomes:
            groups[o.difficulty].append(o)
        return {
            d: GroupStat(total=len(items), passed=sum(1 for i in items if i.passed))
            for d, items in groups.items()
        }

    def summary_dict(self) -> dict:
        return {
            "suite": self.suite,
            "created_at": self.created_at.isoformat(),
            "total": self.total,
            "passed": self.passed,
            "success_rate": round(self.success_rate, 4),
            "mean_score": round(self.mean_score, 4),
            "mean_tokens": round(self.mean_tokens, 1),
            "mean_latency_ms": round(self.mean_latency_ms, 1),
            "blocked_injections": self.blocked_injections,
            "by_category": {
                c: g.model_dump() | {"success_rate": round(g.success_rate, 4)}
                for c, g in self.by_category().items()
            },
            "by_difficulty": {
                d: g.model_dump() | {"success_rate": round(g.success_rate, 4)}
                for d, g in self.by_difficulty().items()
            },
        }
