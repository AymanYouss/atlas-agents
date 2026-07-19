"""Model Context Protocol integration.

:class:`MCPClientManager` attaches one or more MCP servers, discovers the tools
they expose, and wraps each as an Atlas :class:`~atlas.tools.base.Tool` so they
are indistinguishable from built-ins at the call site. This is what makes the
tool layer standards-based: any MCP server (first- or third-party) plugs in with
no code changes.

The reverse direction lives in :mod:`atlas.mcp.server`, which exposes Atlas's own
tools *as* an MCP server so other MCP clients can consume them.
"""

from atlas.mcp.client import MCPClientManager, MCPServerConfig, MCPTransport
from atlas.mcp.server import build_mcp_server

__all__ = [
    "MCPClientManager",
    "MCPServerConfig",
    "MCPTransport",
    "build_mcp_server",
]
