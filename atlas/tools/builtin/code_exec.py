"""Code execution tool that delegates to the hardened Docker sandbox."""

from __future__ import annotations

import asyncio
from typing import Any

from atlas.config import Settings, get_settings
from atlas.sandbox.docker_sandbox import DockerSandbox, SandboxUnavailableError
from atlas.tools.base import Tool, ToolResult, ToolSpec


class CodeExecTool(Tool):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._sandbox = DockerSandbox(self._settings)
        self.spec = ToolSpec(
            name="code_exec",
            description=(
                "Execute a short Python or Bash script in an isolated, network-less "
                "sandbox and return stdout/stderr. Use for calculations, data "
                "wrangling and verification. No internet access inside the sandbox."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Source to execute."},
                    "language": {
                        "type": "string",
                        "enum": ["python", "bash"],
                        "default": "python",
                    },
                },
                "required": ["code"],
            },
        )

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        code = str(arguments.get("code", ""))
        if not code.strip():
            return ToolResult.failure("code_exec requires non-empty 'code'")
        language = str(arguments.get("language", "python"))
        try:
            # The docker SDK is synchronous; run it off the event loop.
            result = await asyncio.to_thread(self._sandbox.run, code, language=language)
        except SandboxUnavailableError as exc:
            return ToolResult.failure(str(exc))
        except ValueError as exc:
            return ToolResult.failure(str(exc))

        rendered = (
            f"exit_code={result.exit_code} timed_out={result.timed_out} "
            f"duration_ms={result.duration_ms}\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )
        return ToolResult(
            ok=result.ok,
            content=rendered,
            data={
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timed_out": result.timed_out,
            },
            error=None if result.ok else "sandbox execution failed",
        )
