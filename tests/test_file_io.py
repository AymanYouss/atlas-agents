from __future__ import annotations

from pathlib import Path

import pytest

from atlas.tools.builtin.file_io import FileIOTool


@pytest.fixture
def tool(tmp_path: Path) -> FileIOTool:
    return FileIOTool(workspace=tmp_path / "ws")


async def test_write_then_read_roundtrip(tool: FileIOTool) -> None:
    w = await tool.invoke({"action": "write", "path": "notes/a.txt", "content": "hello"})
    assert w.ok
    r = await tool.invoke({"action": "read", "path": "notes/a.txt"})
    assert r.ok and r.content == "hello"


async def test_append(tool: FileIOTool) -> None:
    await tool.invoke({"action": "write", "path": "log.txt", "content": "a"})
    await tool.invoke({"action": "append", "path": "log.txt", "content": "b"})
    r = await tool.invoke({"action": "read", "path": "log.txt"})
    assert r.content == "ab"


async def test_list(tool: FileIOTool) -> None:
    await tool.invoke({"action": "write", "path": "x.txt", "content": "1"})
    await tool.invoke({"action": "write", "path": "d/y.txt", "content": "2"})
    r = await tool.invoke({"action": "list"})
    assert set(r.data["files"]) == {"x.txt", "d/y.txt"}


async def test_path_traversal_blocked(tool: FileIOTool) -> None:
    r = await tool.invoke({"action": "read", "path": "../../etc/passwd"})
    assert r.ok is False
    assert "escapes the workspace" in (r.error or "")


async def test_read_missing_file(tool: FileIOTool) -> None:
    r = await tool.invoke({"action": "read", "path": "nope.txt"})
    assert r.ok is False
