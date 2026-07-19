"""The tool registry: the single choke point for every tool invocation.

Centralizing invocation here means allow-list enforcement, latency metrics,
guardrail hooks and event emission all live in one place instead of being
scattered across executor code.
"""

from __future__ import annotations

import time
from collections.abc import Iterable

from atlas.observability.logging import get_logger
from atlas.observability.metrics import TOOL_CALLS_TOTAL, TOOL_LATENCY
from atlas.schemas.run import ToolInvocation
from atlas.tools.base import Tool, ToolResult, ToolSpec

log = get_logger("atlas.tools")


class ToolNotFoundError(KeyError):
    """Raised when a step references a tool that is not registered."""


class ToolNotAllowedError(PermissionError):
    """Raised when a step tries to use a tool outside its declared allow-list."""


class ToolRegistry:
    """Holds all available tools and mediates their invocation."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool, *, replace: bool = False) -> None:
        if tool.name in self._tools and not replace:
            raise ValueError(f"tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool
        log.debug("tool_registered", tool=tool.name, server=tool.spec.server)

    def register_many(self, tools: Iterable[Tool], *, replace: bool = False) -> None:
        for t in tools:
            self.register(t, replace=replace)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(name) from exc

    def has(self, name: str) -> bool:
        return name in self._tools

    def specs(self, *, names: Iterable[str] | None = None) -> list[ToolSpec]:
        if names is None:
            return [t.spec for t in self._tools.values()]
        wanted = set(names)
        return [t.spec for t in self._tools.values() if t.name in wanted]

    async def invoke(
        self,
        name: str,
        arguments: dict,
        *,
        allowed_tools: Iterable[str] | None = None,
    ) -> ToolInvocation:
        """Invoke ``name`` and return a fully-populated :class:`ToolInvocation`.

        If ``allowed_tools`` is provided, the call is rejected unless ``name`` is a
        member — this is how a plan step's tool allow-list is enforced at runtime.
        """
        invocation = ToolInvocation(tool=name, arguments=arguments)

        if allowed_tools is not None and name not in set(allowed_tools):
            invocation.ok = False
            invocation.error = f"tool {name!r} is not in the step's allow-list"
            invocation.finished_at = invocation.started_at
            invocation.duration_ms = 0
            TOOL_CALLS_TOTAL.labels(tool=name, ok="false").inc()
            raise ToolNotAllowedError(invocation.error)

        if not self.has(name):
            invocation.ok = False
            invocation.error = f"unknown tool {name!r}"
            TOOL_CALLS_TOTAL.labels(tool=name, ok="false").inc()
            raise ToolNotFoundError(name)

        tool = self.get(name)
        invocation.server = tool.spec.server
        start = time.perf_counter()
        try:
            result: ToolResult = await tool.invoke(arguments)
        except Exception as exc:  # a tool raising is a failed call, not a crash
            result = ToolResult.failure(str(exc))
            log.warning("tool_invoke_raised", tool=name, error=str(exc))
        duration = time.perf_counter() - start

        invocation.result = {
            "content": result.content,
            "data": result.data,
            "sources": [s.model_dump() for s in result.sources],
        }
        invocation.ok = result.ok
        invocation.error = result.error
        invocation.duration_ms = int(duration * 1000)
        from datetime import UTC, datetime

        invocation.finished_at = datetime.now(UTC)

        TOOL_CALLS_TOTAL.labels(tool=name, ok=str(result.ok).lower()).inc()
        TOOL_LATENCY.labels(tool=name).observe(duration)
        return invocation

    async def aclose(self) -> None:
        for tool in self._tools.values():
            await tool.aclose()
