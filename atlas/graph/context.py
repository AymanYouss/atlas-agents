"""Per-run execution context.

Holds the non-serializable objects a run needs (LLM clients, tool registry,
budget, guardrails, emitter) and is registered in a process-local table keyed by
``run_id``. Graph nodes look their context up by the ``run_id`` in the checkpointed
state, which keeps the persisted state small and JSON-clean.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from atlas.agents.critic import Critic
from atlas.agents.emitter import AgentEmitter, NullEmitter
from atlas.agents.executor import Executor
from atlas.agents.planner import Planner
from atlas.agents.synthesizer import ReportSynthesizer
from atlas.config import Settings, get_settings
from atlas.guardrails.budget import RunBudget
from atlas.guardrails.injection import InjectionScanner
from atlas.llm.base import AgentRole, LLMClient
from atlas.llm.factory import get_llm
from atlas.schemas.run import RunConfig
from atlas.tools.registry import ToolRegistry


@dataclass
class RunContext:
    run_id: str
    goal: str
    config: RunConfig
    registry: ToolRegistry
    budget: RunBudget
    planner: Planner
    executor_llm: LLMClient
    critic: Critic
    synthesizer: ReportSynthesizer
    scanner: InjectionScanner
    emitter: AgentEmitter
    workspace: Path
    settings: Settings
    max_replans: int = 2

    def new_executor(self) -> Executor:
        return Executor(
            self.executor_llm,
            self.registry,
            self.budget,
            scanner=self.scanner,
            emitter=self.emitter,
        )


class _ContextTable:
    def __init__(self) -> None:
        self._contexts: dict[str, RunContext] = {}

    def register(self, ctx: RunContext) -> None:
        self._contexts[ctx.run_id] = ctx

    def get(self, run_id: str) -> RunContext:
        if run_id not in self._contexts:
            raise KeyError(
                f"no RunContext for run {run_id!r}; the orchestrator must register "
                "it before invoking or resuming the graph"
            )
        return self._contexts[run_id]

    def remove(self, run_id: str) -> None:
        self._contexts.pop(run_id, None)


context_table = _ContextTable()


def build_run_context(
    run_id: str,
    goal: str,
    config: RunConfig,
    *,
    registry: ToolRegistry,
    workspace: Path,
    emitter: AgentEmitter | None = None,
    settings: Settings | None = None,
    llms: dict[AgentRole, LLMClient] | None = None,
) -> RunContext:
    """Assemble a fully-wired :class:`RunContext`.

    ``llms`` lets callers (tests, evals) inject a deterministic client for every
    role; in production the clients are resolved from settings.
    """
    settings = settings or get_settings()
    llms = llms or {
        role: get_llm(role, settings=settings)
        for role in (AgentRole.PLANNER, AgentRole.EXECUTOR, AgentRole.CRITIC)
    }
    emitter = emitter or NullEmitter()
    budget = RunBudget(
        max_steps=config.max_steps or settings.max_steps,
        max_retries_per_step=config.max_retries_per_step or settings.max_retries_per_step,
        max_tokens=settings.max_tokens_per_run,
        max_wall_clock_seconds=settings.max_wall_clock_seconds,
    )
    ctx = RunContext(
        run_id=run_id,
        goal=goal,
        config=config,
        registry=registry,
        budget=budget,
        planner=Planner(llms[AgentRole.PLANNER]),
        executor_llm=llms[AgentRole.EXECUTOR],
        critic=Critic(llms[AgentRole.CRITIC]),
        synthesizer=ReportSynthesizer(llms[AgentRole.CRITIC], emitter=emitter),
        scanner=InjectionScanner(),
        emitter=emitter,
        workspace=workspace,
        settings=settings,
    )
    context_table.register(ctx)
    return ctx
