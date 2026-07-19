"""A minimal event-emitter seam so agents can stream progress without importing
the graph or persistence layers (which would create an import cycle)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from atlas.observability.events import EventType


@runtime_checkable
class AgentEmitter(Protocol):
    async def emit(
        self,
        type: EventType,
        *,
        step_id: str | None = None,
        agent: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None: ...


class NullEmitter:
    """Discards all events. Default for unit tests and library usage."""

    async def emit(
        self,
        type: EventType,
        *,
        step_id: str | None = None,
        agent: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        return None
