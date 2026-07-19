from __future__ import annotations

from typing import Any

import pytest

from atlas.tools.base import Tool, ToolResult, ToolSpec
from atlas.tools.registry import ToolNotAllowedError, ToolNotFoundError, ToolRegistry


class EchoTool(Tool):
    def __init__(self, name: str = "echo") -> None:
        self.spec = ToolSpec(name=name, description="echo back its args")

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(ok=True, content=str(arguments), data=arguments)


class BoomTool(Tool):
    def __init__(self) -> None:
        self.spec = ToolSpec(name="boom", description="always raises")

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        raise RuntimeError("kaboom")


@pytest.fixture
def registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register(EchoTool())
    r.register(BoomTool())
    return r


async def test_invoke_records_metadata(registry: ToolRegistry) -> None:
    inv = await registry.invoke("echo", {"a": 1})
    assert inv.ok is True
    assert inv.tool == "echo"
    assert inv.duration_ms is not None and inv.duration_ms >= 0
    assert inv.finished_at is not None


async def test_allowlist_blocks_disallowed_tool(registry: ToolRegistry) -> None:
    with pytest.raises(ToolNotAllowedError):
        await registry.invoke("echo", {}, allowed_tools=["web_search"])


async def test_allowlist_permits_listed_tool(registry: ToolRegistry) -> None:
    inv = await registry.invoke("echo", {"x": 2}, allowed_tools=["echo"])
    assert inv.ok is True


async def test_unknown_tool_raises(registry: ToolRegistry) -> None:
    with pytest.raises(ToolNotFoundError):
        await registry.invoke("ghost", {})


async def test_tool_exception_becomes_failed_invocation(registry: ToolRegistry) -> None:
    inv = await registry.invoke("boom", {})
    assert inv.ok is False
    assert inv.error and "kaboom" in inv.error


def test_duplicate_registration_rejected(registry: ToolRegistry) -> None:
    with pytest.raises(ValueError, match="already registered"):
        registry.register(EchoTool())


def test_specs_filtering(registry: ToolRegistry) -> None:
    names = {s.name for s in registry.specs(names=["echo"])}
    assert names == {"echo"}
