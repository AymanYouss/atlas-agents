"""Run lifecycle orchestration on top of the graph and the repository.

Responsibilities:

* create and persist runs;
* execute a run in the background, persisting every event for durable replay;
* pause at approval gates and resume with a reviewer's decisions;
* project terminal/paused graph state back into the stored :class:`RunRecord`.
"""

from __future__ import annotations

import asyncio
import uuid

from atlas.graph.emitter import RunEmitter
from atlas.graph.orchestrator import Orchestrator
from atlas.llm.base import AgentRole, LLMClient
from atlas.observability.events import EventType, RunEvent, event_broker
from atlas.observability.logging import get_logger
from atlas.persistence.records import EventRecord, RunRecord
from atlas.persistence.repository import RunRepository
from atlas.schemas.run import RunConfig, RunStatus

log = get_logger("atlas.run_manager")


class RunManager:
    def __init__(
        self,
        orchestrator: Orchestrator,
        repository: RunRepository,
        *,
        llm_override: dict[AgentRole, LLMClient] | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._repo = repository
        self._llms = llm_override
        self._tasks: dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------ create
    async def create_run(
        self, goal: str, *, config: RunConfig | None = None, tags: list[str] | None = None
    ) -> RunRecord:
        config = config or RunConfig()
        record = RunRecord(
            id=f"run_{uuid.uuid4().hex[:16]}",
            goal=goal,
            status=RunStatus.PENDING,
            config=config.model_dump(mode="json"),
            tags=tags or config.tags,
        )
        await self._repo.create(record)
        log.info("run_created", run_id=record.id, goal=goal)
        return record

    def launch(self, run_id: str, goal: str, config: RunConfig) -> None:
        """Fire-and-forget background execution of a created run."""
        self._tasks[run_id] = asyncio.create_task(self._execute(run_id, goal, config))

    # ------------------------------------------------------------------- reads
    async def get_run(self, run_id: str) -> RunRecord | None:
        return await self._repo.get(run_id)

    async def list_runs(self, *, limit: int = 50, offset: int = 0) -> list[RunRecord]:
        return await self._repo.list_runs(limit=limit, offset=offset)

    async def replay_events(self, run_id: str, *, after_seq: int = 0) -> list[EventRecord]:
        return await self._repo.list_events(run_id, after_seq=after_seq)

    # -------------------------------------------------------------- approvals
    async def submit_approval(self, run_id: str, decisions: dict) -> RunRecord | None:
        record = await self._repo.get(run_id)
        if record is None or record.status is not RunStatus.AWAITING_APPROVAL:
            return record
        self._tasks[run_id] = asyncio.create_task(self._resume(run_id, decisions))
        return record

    # -------------------------------------------------------------- execution
    def _emitter(self, run_id: str) -> RunEmitter:
        async def _persist(event: RunEvent) -> None:
            await self._repo.append_event(
                EventRecord(
                    run_id=event.run_id,
                    seq=event.seq,
                    type=str(event.type),
                    step_id=event.step_id,
                    agent=event.agent,
                    payload=event.payload,
                    ts=event.ts,
                )
            )
            await self._project(event)

        return RunEmitter(run_id, broker=event_broker, on_event=_persist)

    async def _project(self, event: RunEvent) -> None:
        """Reflect a handful of key events into the stored record for snapshot reads."""
        if event.type not in {EventType.PLAN_CREATED, EventType.RUN_STATUS}:
            return
        record = await self._repo.get(event.run_id)
        if record is None:
            return
        if event.type is EventType.PLAN_CREATED and not record.plan:
            record.plan = event.payload.get("plan")
        elif event.type is EventType.RUN_STATUS:
            status = event.payload.get("status")
            if status and record.status not in {RunStatus.COMPLETED, RunStatus.FAILED}:
                record.status = RunStatus(status)
        await self._repo.update(record)

    async def _execute(self, run_id: str, goal: str, config: RunConfig) -> None:
        try:
            state = await self._orchestrator.start(
                run_id=run_id,
                goal=goal,
                config=config,
                emitter=self._emitter(run_id),
                llms=self._llms,
            )
            await self._finish(run_id, state)
        except Exception as exc:  # a crash must still leave a coherent record
            log.exception("run_failed", run_id=run_id)
            await self._mark_failed(run_id, str(exc))

    async def _resume(self, run_id: str, decisions: dict) -> None:
        try:
            state = await self._orchestrator.resume(run_id=run_id, decisions=decisions)
            await self._finish(run_id, state)
        except Exception as exc:
            log.exception("run_resume_failed", run_id=run_id)
            await self._mark_failed(run_id, str(exc))

    async def _finish(self, run_id: str, state: dict) -> None:
        record = await self._repo.get(run_id)
        if record is None:
            return
        pending = self._orchestrator.pending_approvals(state)
        record.plan = state.get("plan") or record.plan
        record.results = state.get("results", {})
        record.critiques = state.get("critiques", [])
        record.report = state.get("report")
        record.approvals = state.get("approvals", {})

        if pending:
            record.status = RunStatus.AWAITING_APPROVAL
            record.pending_approvals = pending
        else:
            record.pending_approvals = []
            record.status = RunStatus(state.get("status", RunStatus.COMPLETED))
            record.error = state.get("error")
            # The run reached a terminal state; release the in-memory context.
            if record.status.is_terminal:
                self._orchestrator.release(run_id)
        await self._repo.update(record)
        log.info("run_finished", run_id=run_id, status=str(record.status))

    async def _mark_failed(self, run_id: str, error: str) -> None:
        record = await self._repo.get(run_id)
        if record is None:
            return
        record.status = RunStatus.FAILED
        record.error = error
        await self._repo.update(record)
        self._orchestrator.release(run_id)
