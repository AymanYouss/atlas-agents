"""Concrete run emitter that publishes to the in-process event broker.

Implements the :class:`~atlas.agents.emitter.AgentEmitter` protocol. A persistence
hook can be layered on by passing an ``on_event`` callback (the API layer uses
this to append events to Postgres for durable replay).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from atlas.observability.events import EventBroker, EventType, RunEvent, event_broker


class RunEmitter:
    def __init__(
        self,
        run_id: str,
        *,
        broker: EventBroker | None = None,
        on_event: Callable[[RunEvent], Awaitable[None]] | None = None,
    ) -> None:
        self._run_id = run_id
        self._broker = broker or event_broker
        self._on_event = on_event

    async def emit(
        self,
        type: EventType,
        *,
        step_id: str | None = None,
        agent: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = RunEvent(
            run_id=self._run_id,
            type=type,
            step_id=step_id,
            agent=agent,
            payload=payload or {},
        )
        published = await self._broker.publish(event)
        if self._on_event is not None:
            await self._on_event(published)
