"""MCP client manager: attach servers, discover tools, wrap them as Atlas tools."""

from __future__ import annotations

from contextlib import AsyncExitStack
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from atlas.observability.logging import get_logger
from atlas.tools.base import Tool, ToolResult, ToolSource, ToolSpec

log = get_logger("atlas.mcp")


class MCPTransport(StrEnum):
    STDIO = "stdio"
    SSE = "sse"


class MCPServerConfig(BaseModel):
    """How to reach a single MCP server."""

    name: str
    transport: MCPTransport = MCPTransport.STDIO
    # stdio
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    # sse
    url: str | None = None
    # Only expose these tools (empty = all discovered tools).
    allowlist: list[str] = Field(default_factory=list)


class MCPTool(Tool):
    """An Atlas tool that proxies calls to a remote MCP tool over a live session."""

    def __init__(
        self, session: Any, server_name: str, name: str, description: str, input_schema: dict
    ) -> None:
        self._session = session
        self.spec = ToolSpec(
            name=name,
            description=description,
            server=server_name,
            source=ToolSource.MCP,
            input_schema=input_schema or {},
        )

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            result = await self._session.call_tool(self.spec.name, arguments)
        except Exception as exc:  # network / protocol error
            return ToolResult.failure(f"MCP call failed: {exc}")

        text = _render_content(getattr(result, "content", []))
        if getattr(result, "isError", False):
            return ToolResult.failure(text or "MCP tool reported an error")
        return ToolResult(ok=True, content=text, data={"raw": text})


class MCPClientManager:
    """Owns the lifetime of all attached MCP sessions.

    Sessions are opened on :meth:`connect_all` and held on an
    :class:`AsyncExitStack` until :meth:`aclose`, so proxied tools can be called
    at any point during a run.
    """

    def __init__(self, servers: list[MCPServerConfig] | None = None) -> None:
        self._servers = servers or []
        self._stack = AsyncExitStack()
        self._tools: list[MCPTool] = []
        self._connected = False

    async def connect_all(self) -> list[MCPTool]:
        if self._connected:
            return self._tools
        for cfg in self._servers:
            try:
                await self._connect_one(cfg)
            except Exception as exc:  # a bad server must not sink the whole run
                log.warning("mcp_connect_failed", server=cfg.name, error=str(exc))
        self._connected = True
        return self._tools

    async def _connect_one(self, cfg: MCPServerConfig) -> None:
        from mcp import ClientSession

        if cfg.transport is MCPTransport.STDIO:
            from mcp.client.stdio import stdio_client

            from mcp import StdioServerParameters

            if not cfg.command:
                raise ValueError(f"stdio MCP server {cfg.name!r} needs a command")
            params = StdioServerParameters(command=cfg.command, args=cfg.args, env=cfg.env)
            read, write = await self._stack.enter_async_context(stdio_client(params))
        else:
            from mcp.client.sse import sse_client

            if not cfg.url:
                raise ValueError(f"sse MCP server {cfg.name!r} needs a url")
            read, write = await self._stack.enter_async_context(sse_client(cfg.url))

        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        listed = await session.list_tools()

        allow = set(cfg.allowlist)
        for t in listed.tools:
            if allow and t.name not in allow:
                continue
            schema = getattr(t, "inputSchema", None) or {}
            self._tools.append(MCPTool(session, cfg.name, t.name, t.description or "", schema))
            log.info("mcp_tool_registered", server=cfg.name, tool=t.name)

    async def aclose(self) -> None:
        await self._stack.aclose()
        self._connected = False


def _render_content(content: list[Any]) -> str:
    parts: list[str] = []
    for block in content or []:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(str(block))
    return "\n".join(parts)
