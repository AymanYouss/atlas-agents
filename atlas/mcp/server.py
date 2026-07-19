"""Expose Atlas's built-in tools as a standalone MCP server.

Run with ``python -m atlas.mcp.server`` (stdio transport). This lets any MCP
client — including another Atlas instance, Claude Desktop, or a third-party
agent — consume Atlas's web-search, code-execution and file-I/O tools over the
standard protocol.
"""

from __future__ import annotations

import tempfile
from pathlib import Path


def build_mcp_server(workspace: Path | None = None):
    """Construct a FastMCP server wrapping the built-in tools."""
    from mcp.server.fastmcp import FastMCP

    from atlas.tools.builtin import CodeExecTool, FileIOTool, HttpFetchTool, WebSearchTool

    ws = workspace or Path(tempfile.mkdtemp(prefix="atlas-mcp-"))
    server = FastMCP("atlas-tools")
    web = WebSearchTool()
    fetch = HttpFetchTool()
    code = CodeExecTool()
    files = FileIOTool(workspace=ws)

    @server.tool(description=web.spec.description)
    async def web_search(query: str, max_results: int = 5) -> str:
        return (await web.invoke({"query": query, "max_results": max_results})).content

    @server.tool(description=fetch.spec.description)
    async def http_fetch(url: str) -> str:
        return (await fetch.invoke({"url": url})).content

    @server.tool(description=code.spec.description)
    async def code_exec(code_source: str, language: str = "python") -> str:
        return (await code.invoke({"code": code_source, "language": language})).content

    @server.tool(description=files.spec.description)
    async def file_io(action: str, path: str = "", content: str = "") -> str:
        return (await files.invoke({"action": action, "path": path, "content": content})).content

    return server


def main() -> None:
    build_mcp_server().run()


if __name__ == "__main__":
    main()
