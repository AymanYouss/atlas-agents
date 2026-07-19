"""Built-in, in-process tools bundled with Atlas."""

from __future__ import annotations

from pathlib import Path

from atlas.config import Settings, get_settings
from atlas.tools.base import Tool
from atlas.tools.builtin.code_exec import CodeExecTool
from atlas.tools.builtin.file_io import FileIOTool
from atlas.tools.builtin.http_fetch import HttpFetchTool
from atlas.tools.builtin.web_search import WebSearchTool


def default_tools(*, workspace: Path, settings: Settings | None = None) -> list[Tool]:
    """Construct the standard tool set for a run bound to ``workspace``."""
    settings = settings or get_settings()
    return [
        WebSearchTool(settings=settings),
        HttpFetchTool(),
        CodeExecTool(settings=settings),
        FileIOTool(workspace=workspace),
    ]


__all__ = [
    "CodeExecTool",
    "FileIOTool",
    "HttpFetchTool",
    "WebSearchTool",
    "default_tools",
]
