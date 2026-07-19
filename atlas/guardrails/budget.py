"""Hard runtime budgets that bound cost and stop runaway loops."""

from __future__ import annotations

import time
from collections import Counter
from enum import StrEnum

from pydantic import BaseModel

from atlas.observability.metrics import GUARDRAIL_BLOCKS


class BudgetKind(StrEnum):
    STEPS = "steps"
    RETRIES = "retries"
    TOKENS = "tokens"
    WALL_CLOCK = "wall_clock"
    LOOP = "loop"


class BudgetExceededError(RuntimeError):
    """Raised when a run exceeds one of its hard ceilings."""

    def __init__(self, kind: BudgetKind, message: str) -> None:
        self.kind = kind
        super().__init__(message)


class RunawayLoopError(BudgetExceededError):
    """Raised when the same action is repeated enough times to look like a loop."""

    def __init__(self, message: str) -> None:
        super().__init__(BudgetKind.LOOP, message)


class BudgetSnapshot(BaseModel):
    steps_used: int
    tokens_used: int
    elapsed_seconds: float
    max_steps: int
    max_tokens: int
    max_wall_clock_seconds: int


class RunBudget:
    """Tracks and enforces per-run limits.

    All ``charge_*`` methods raise :class:`BudgetExceededError` the moment a limit
    is crossed, so the orchestrator can fail the run cleanly instead of looping or
    over-spending. Repeated identical actions are detected separately as a
    runaway loop even when the numeric budgets still have headroom.
    """

    def __init__(
        self,
        *,
        max_steps: int,
        max_retries_per_step: int,
        max_tokens: int,
        max_wall_clock_seconds: int,
        loop_repeat_threshold: int = 3,
    ) -> None:
        self.max_steps = max_steps
        self.max_retries_per_step = max_retries_per_step
        self.max_tokens = max_tokens
        self.max_wall_clock_seconds = max_wall_clock_seconds
        self._loop_repeat_threshold = loop_repeat_threshold

        self.steps_used = 0
        self.tokens_used = 0
        self._retries: Counter[str] = Counter()
        self._action_fingerprints: Counter[str] = Counter()
        self._start = time.monotonic()

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._start

    def _block(self, kind: BudgetKind, message: str) -> None:
        GUARDRAIL_BLOCKS.labels(guardrail=f"budget_{kind}").inc()
        raise BudgetExceededError(kind, message)

    def charge_step(self) -> None:
        self.check_wall_clock()
        if self.steps_used >= self.max_steps:
            self._block(BudgetKind.STEPS, f"step budget exhausted (max_steps={self.max_steps})")
        self.steps_used += 1

    def charge_retry(self, step_id: str) -> int:
        self._retries[step_id] += 1
        if self._retries[step_id] > self.max_retries_per_step:
            self._block(
                BudgetKind.RETRIES,
                f"retry budget exhausted for step {step_id!r} "
                f"(max_retries_per_step={self.max_retries_per_step})",
            )
        return self._retries[step_id]

    def charge_tokens(self, n: int) -> None:
        self.tokens_used += max(0, n)
        if self.tokens_used > self.max_tokens:
            self._block(BudgetKind.TOKENS, f"token budget exhausted (max_tokens={self.max_tokens})")

    def check_wall_clock(self) -> None:
        if self.elapsed_seconds > self.max_wall_clock_seconds:
            self._block(
                BudgetKind.WALL_CLOCK,
                f"wall-clock budget exhausted "
                f"(max_wall_clock_seconds={self.max_wall_clock_seconds})",
            )

    def record_action(self, fingerprint: str) -> None:
        """Track a tool call's (tool + args) fingerprint and flag tight loops."""
        self._action_fingerprints[fingerprint] += 1
        if self._action_fingerprints[fingerprint] >= self._loop_repeat_threshold:
            GUARDRAIL_BLOCKS.labels(guardrail="budget_loop").inc()
            raise RunawayLoopError(
                f"identical action repeated {self._action_fingerprints[fingerprint]} times; "
                "aborting to prevent a runaway loop"
            )

    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(
            steps_used=self.steps_used,
            tokens_used=self.tokens_used,
            elapsed_seconds=round(self.elapsed_seconds, 3),
            max_steps=self.max_steps,
            max_tokens=self.max_tokens,
            max_wall_clock_seconds=self.max_wall_clock_seconds,
        )
