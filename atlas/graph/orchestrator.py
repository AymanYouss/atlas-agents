"""The orchestrator: the public entry point for running and resuming agents.

Owns the compiled graph and the checkpointer, builds a run's tool registry and
context, and exposes a small surface (``start``, ``resume``, ``snapshot``) that
the API and CLI share. With a Postgres checkpointer this is fully durable: a
process can crash mid-run and another can resume from the last checkpoint.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from atlas.agents.emitter import AgentEmitter
from atlas.config import Settings, get_settings
from atlas.graph.build import build_graph
from atlas.graph.context import build_run_context, context_table
from atlas.graph.emitter import RunEmitter
from atlas.llm.base import AgentRole, LLMClient
from atlas.observability.events import EventType
from atlas.observability.logging import get_logger
from atlas.observability.metrics import ACTIVE_RUNS, RUNS_TOTAL
from atlas.schemas.run import RunConfig, RunStatus
from atlas.tools.registry import ToolRegistry

log = get_logger("atlas.orchestrator")


class Orchestrator:
    def __init__(
        self, *, checkpointer: Any | None = None, settings: Settings | None = None
    ) -> None:
        self.settings = settings or get_settings()
        self.checkpointer = checkpointer or MemorySaver()
        self.graph = build_graph(self.checkpointer)
        self._runs_root = Path(".data/runs")

    def _config(self, run_id: str) -> dict:
        return {"configurable": {"thread_id": run_id}, "recursion_limit": 100}

    def default_registry(self, workspace: Path) -> ToolRegistry:
        from atlas.tools.builtin import default_tools

        registry = ToolRegistry()
        registry.register_many(default_tools(workspace=workspace, settings=self.settings))
        return registry

    async def start(
        self,
        *,
        run_id: str,
        goal: str,
        config: RunConfig | None = None,
        registry: ToolRegistry | None = None,
        workspace: Path | None = None,
        emitter: AgentEmitter | None = None,
        llms: dict[AgentRole, LLMClient] | None = None,
    ) -> dict:
        config = config or RunConfig()
        workspace = workspace or (self._runs_root / run_id)
        workspace.mkdir(parents=True, exist_ok=True)
        registry = registry or self.default_registry(workspace)
        emitter = emitter or RunEmitter(run_id)

        build_run_context(
            run_id,
            goal,
            config,
            registry=registry,
            workspace=workspace,
            emitter=emitter,
            settings=self.settings,
            llms=llms,
        )
        await emitter.emit(EventType.RUN_CREATED, payload={"goal": goal})
        ACTIVE_RUNS.inc()
        try:
            initial: dict = {
                "run_id": run_id,
                "goal": goal,
                "results": {},
                "critiques": [],
                "approvals": {},
                "replans": 0,
                "status": RunStatus.PENDING,
                "error": None,
            }
            state = await self.graph.ainvoke(initial, self._config(run_id))
            self._record_terminal(state)
            return state
        finally:
            ACTIVE_RUNS.dec()

    async def resume(self, *, run_id: str, decisions: dict) -> dict:
        """Resume a run paused at a human approval gate with the reviewer's decisions."""
        if run_id not in _has_context(run_id):
            raise RuntimeError(f"run {run_id!r} has no live context; rebuild it before resuming.")
        ACTIVE_RUNS.inc()
        try:
            state = await self.graph.ainvoke(Command(resume=decisions), self._config(run_id))
            self._record_terminal(state)
            return state
        finally:
            ACTIVE_RUNS.dec()

    def snapshot(self, run_id: str):
        return self.graph.get_state(self._config(run_id))

    @staticmethod
    def pending_approvals(state: dict) -> list[dict]:
        """Extract approval requests from an interrupted run's state, if any."""
        interrupts = state.get("__interrupt__")
        if not interrupts:
            return []
        approvals: list[dict] = []
        for it in interrupts:
            value = getattr(it, "value", it)
            if isinstance(value, dict):
                approvals.extend(value.get("approvals", []))
        return approvals

    def _record_terminal(self, state: dict) -> None:
        status = state.get("status")
        if status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            RUNS_TOTAL.labels(status=str(status)).inc()

    def release(self, run_id: str) -> None:
        context_table.remove(run_id)


def _has_context(run_id: str) -> set[str]:
    try:
        context_table.get(run_id)
        return {run_id}
    except KeyError:
        return set()
