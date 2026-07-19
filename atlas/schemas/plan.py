"""The plan produced by the planner and consumed by the executor.

A plan is a directed acyclic graph of steps. Each step declares the tools it is
allowed to use and the ids of the steps it depends on, which lets the executor
run independent branches concurrently while respecting data dependencies.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class StepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(BaseModel):
    """A single unit of work in the plan."""

    id: str = Field(description="Stable, human-readable id, e.g. 'step-3'.")
    title: str = Field(description="Short imperative description of the step.")
    detail: str = Field(
        default="",
        description="Full instruction handed to the executor agent for this step.",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Ids of steps that must succeed before this one becomes ready.",
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        description="Tool names this step may call. Empty means reasoning-only.",
    )
    requires_approval: bool = Field(
        default=False,
        description="If true, execution pauses for a human approval gate before running.",
    )
    status: StepStatus = StepStatus.PENDING

    @model_validator(mode="after")
    def _no_self_dependency(self) -> PlanStep:
        if self.id in self.depends_on:
            raise ValueError(f"step {self.id!r} cannot depend on itself")
        return self


class Plan(BaseModel):
    """An ordered, dependency-aware decomposition of the user's goal."""

    goal: str
    rationale: str = Field(
        default="",
        description="The planner's short justification for this decomposition.",
    )
    steps: list[PlanStep] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_dag(self) -> Plan:
        ids = [s.id for s in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("plan step ids must be unique")
        known = set(ids)
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in known:
                    raise ValueError(f"step {step.id!r} depends on unknown step {dep!r}")
        self._assert_acyclic()
        return self

    def _assert_acyclic(self) -> None:
        graph = {s.id: set(s.depends_on) for s in self.steps}
        visited: set[str] = set()
        stack: set[str] = set()

        def walk(node: str) -> None:
            if node in stack:
                raise ValueError(f"plan contains a cycle at step {node!r}")
            if node in visited:
                return
            stack.add(node)
            for dep in graph[node]:
                walk(dep)
            stack.discard(node)
            visited.add(node)

        for node in graph:
            walk(node)

    def step(self, step_id: str) -> PlanStep:
        for s in self.steps:
            if s.id == step_id:
                return s
        raise KeyError(step_id)

    def ready_steps(self, completed: set[str]) -> list[PlanStep]:
        """Return pending steps whose dependencies are all satisfied."""
        return [
            s
            for s in self.steps
            if s.status is StepStatus.PENDING
            and s.id not in completed
            and set(s.depends_on) <= completed
        ]
