"""Tool abstractions shared by built-in and MCP-backed tools."""

from __future__ import annotations

import abc
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ToolSource(StrEnum):
    BUILTIN = "builtin"
    MCP = "mcp"


class ToolSpec(BaseModel):
    """Declarative description of a tool, surfaced to the planner and the UI."""

    name: str
    description: str
    server: str = Field(default="builtin", description="Owning MCP server or 'builtin'.")
    source: ToolSource = ToolSource.BUILTIN
    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for the tool's arguments."
    )
    requires_approval: bool = Field(
        default=False,
        description="If true, the executor pauses for a human gate before every call.",
    )
    produces_citations: bool = Field(
        default=False,
        description="Whether results carry sources that can back report claims.",
    )


class SourceRef(BaseModel):
    """A citable source returned by a tool (e.g. a search hit or a fetched page)."""

    title: str = ""
    url: str | None = None
    snippet: str = ""


class ToolResult(BaseModel):
    """The normalized outcome of a tool invocation."""

    ok: bool = True
    content: str = Field(default="", description="Human/LLM-readable rendering of the result.")
    data: Any = Field(default=None, description="Structured payload for programmatic use.")
    sources: list[SourceRef] = Field(default_factory=list)
    error: str | None = None

    @classmethod
    def failure(cls, error: str) -> ToolResult:
        return cls(ok=False, error=error, content=f"Tool error: {error}")


class Tool(abc.ABC):
    """A callable capability. Concrete tools implement :meth:`invoke`."""

    spec: ToolSpec

    @property
    def name(self) -> str:
        return self.spec.name

    @abc.abstractmethod
    async def invoke(self, arguments: dict[str, Any]) -> ToolResult: ...

    async def aclose(self) -> None:
        """Release any resources (network sessions, MCP connections)."""
        return None
