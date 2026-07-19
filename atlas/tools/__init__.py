"""The tool layer.

Executor agents never call tools directly; they go through the
:class:`~atlas.tools.registry.ToolRegistry`, which enforces per-step allow-lists,
records every invocation, and emits telemetry. Tools come from two sources:

* **Built-in tools** (``atlas.tools.builtin``) — web search, sandboxed code
  execution and workspace file I/O, implemented in-process for low latency.
* **MCP tools** (``atlas.mcp``) — any Model Context Protocol server can be
  attached at runtime; its tools are discovered and registered exactly like the
  built-ins, which is what makes the tool layer standards-based and swappable.
"""

from atlas.tools.base import Tool, ToolResult, ToolSource, ToolSpec
from atlas.tools.registry import ToolNotAllowedError, ToolNotFoundError, ToolRegistry

__all__ = [
    "Tool",
    "ToolNotAllowedError",
    "ToolNotFoundError",
    "ToolRegistry",
    "ToolResult",
    "ToolSource",
    "ToolSpec",
]
