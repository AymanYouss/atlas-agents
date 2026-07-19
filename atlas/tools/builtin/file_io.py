"""Workspace-scoped file I/O.

Every run gets its own workspace directory. All paths are resolved against it and
validated to stay inside it, so a step can never read or write outside its own
sandboxed working area (no path traversal via ``..`` or absolute paths).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from atlas.tools.base import Tool, ToolResult, ToolSpec

_MAX_BYTES = 1_000_000


class FileIOTool(Tool):
    def __init__(self, *, workspace: Path) -> None:
        self._root = Path(workspace).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self.spec = ToolSpec(
            name="file_io",
            description=(
                "Read, write, append to and list files in the run's private "
                "workspace. Use to persist intermediate artifacts between steps."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["read", "write", "append", "list"]},
                    "path": {"type": "string", "description": "Path relative to the workspace."},
                    "content": {"type": "string", "description": "Content for write/append."},
                },
                "required": ["action"],
            },
        )

    def _resolve(self, rel: str) -> Path:
        candidate = (self._root / rel).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise ValueError(f"path {rel!r} escapes the workspace")
        return candidate

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        action = str(arguments.get("action", "")).lower()
        try:
            if action == "list":
                return self._list()
            path = str(arguments.get("path", "")).strip()
            if not path:
                return ToolResult.failure("file_io requires 'path' for this action")
            target = self._resolve(path)
            if action == "read":
                return self._read(target, path)
            if action in {"write", "append"}:
                return self._write(target, path, str(arguments.get("content", "")), action)
            return ToolResult.failure(f"unknown file_io action {action!r}")
        except ValueError as exc:
            return ToolResult.failure(str(exc))

    def _list(self) -> ToolResult:
        entries = sorted(
            str(p.relative_to(self._root)) for p in self._root.rglob("*") if p.is_file()
        )
        return ToolResult(
            ok=True, content="\n".join(entries) or "(workspace is empty)", data={"files": entries}
        )

    def _read(self, target: Path, rel: str) -> ToolResult:
        if not target.is_file():
            return ToolResult.failure(f"no such file: {rel}")
        if target.stat().st_size > _MAX_BYTES:
            return ToolResult.failure(f"file too large to read: {rel}")
        text = target.read_text(encoding="utf-8", errors="replace")
        return ToolResult(ok=True, content=text, data={"path": rel, "bytes": len(text)})

    def _write(self, target: Path, rel: str, content: str, action: str) -> ToolResult:
        if len(content.encode()) > _MAX_BYTES:
            return ToolResult.failure("content exceeds the 1MB per-file limit")
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if action == "append" else "w"
        with target.open(mode, encoding="utf-8") as fh:
            fh.write(content)
        return ToolResult(
            ok=True,
            content=f"{action} ok: {rel} ({len(content)} chars)",
            data={"path": rel, "bytes": len(content)},
        )
