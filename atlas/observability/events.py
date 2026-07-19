"""The run-event stream.

Every meaningful moment in a run (plan produced, step started, tool called,
token streamed, approval requested, critic verdict, report ready) is published
as a :class:`RunEvent`. The API layer subscribes per run and forwards events to
the browser over Server-Sent Events, which is what powers the live run
visualizer.

The broker is an in-process asyncio fan-out. In a multi-replica deployment the
same interface is backed by Postgres ``LISTEN/NOTIFY`` (see
``atlas/persistence/pubsub.py``); the API contract is identical.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    RUN_CREATED = "run_created"
    RUN_STATUS = "run_status"
    PLAN_CREATED = "plan_created"
    STEP_STATUS = "step_status"
    AGENT_TOKEN = "agent_token"
    AGENT_MESSAGE = "agent_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"
    CRITIQUE = "critique"
    GUARDRAIL = "guardrail"
    REPORT_READY = "report_ready"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class RunEvent(BaseModel):
    """A single event on a run's timeline."""

    run_id: str
    type: EventType
    seq: int = 0
    step_id: str | None = None
    agent: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EventBroker:
    """In-process pub/sub fan-out keyed by run id.

    Late subscribers receive the full replay buffer for the run first, then live
    events, so a browser that connects mid-run still renders the whole timeline.
    """

    def __init__(self, replay_buffer_size: int = 2048) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[RunEvent]]] = defaultdict(set)
        self._replay: dict[str, list[RunEvent]] = defaultdict(list)
        self._seq: dict[str, int] = defaultdict(int)
        self._buffer_size = replay_buffer_size
        self._lock = asyncio.Lock()

    async def publish(self, event: RunEvent) -> RunEvent:
        async with self._lock:
            self._seq[event.run_id] += 1
            event.seq = self._seq[event.run_id]
            buf = self._replay[event.run_id]
            buf.append(event)
            if len(buf) > self._buffer_size:
                del buf[: len(buf) - self._buffer_size]
            subscribers = list(self._subscribers[event.run_id])
        for q in subscribers:
            q.put_nowait(event)
        return event

    async def subscribe(self, run_id: str, *, replay: bool = True) -> AsyncIterator[RunEvent]:
        queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=1024)
        async with self._lock:
            if replay:
                for event in self._replay[run_id]:
                    queue.put_nowait(event)
            self._subscribers[run_id].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            async with self._lock:
                self._subscribers[run_id].discard(queue)

    def replay(self, run_id: str) -> list[RunEvent]:
        return list(self._replay[run_id])

    async def close(self, run_id: str) -> None:
        async with self._lock:
            self._subscribers.pop(run_id, None)
            self._replay.pop(run_id, None)
            self._seq.pop(run_id, None)


# Process-wide singleton used by the graph and API layers.
event_broker = EventBroker()
