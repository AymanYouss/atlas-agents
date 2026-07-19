"""Locked-down code execution backed by Docker.

Untrusted, model-generated code is the single largest attack surface in an agent
platform, so the sandbox is defense-in-depth by default:

* no network (``--network none``);
* dropped Linux capabilities and ``no-new-privileges``;
* read-only root filesystem with a size-capped ``tmpfs`` workspace;
* CPU, memory and PID limits;
* a non-root user;
* a hard wall-clock timeout enforced by killing the container.

The interface (:meth:`DockerSandbox.run`) is transport-agnostic: the same method
can be fronted by a Firecracker microVM driver for stronger isolation in
production without changing any caller. See ``deploy/docker/Dockerfile.sandbox``
for the runtime image.
"""

from __future__ import annotations

import io
import tarfile
import uuid
from dataclasses import dataclass, field

from atlas.config import Settings, get_settings
from atlas.observability.logging import get_logger

log = get_logger("atlas.sandbox")

_LANG_CMD = {
    "python": ["python", "/workspace/main.py"],
    "bash": ["bash", "/workspace/main.sh"],
}
_LANG_FILE = {"python": "main.py", "bash": "main.sh"}


class SandboxUnavailableError(RuntimeError):
    """Raised when the Docker daemon cannot be reached."""


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_ms: int = 0
    artifacts: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class DockerSandbox:
    """Runs a single code snippet in a throwaway, hardened container."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _client(self):
        try:
            import docker

            client = docker.from_env()
            client.ping()
            return client
        except Exception as exc:  # daemon missing / not reachable
            raise SandboxUnavailableError(
                "Docker daemon is not reachable; the code sandbox is unavailable."
            ) from exc

    def _nano_cpus(self) -> int:
        return int(self._settings.sandbox_cpu_limit * 1_000_000_000)

    def run(
        self,
        code: str,
        *,
        language: str = "python",
        extra_files: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute ``code`` and return its captured output.

        ``extra_files`` are written into the workspace alongside the entrypoint so
        multi-file snippets and small input datasets work.
        """
        if language not in _LANG_CMD:
            raise ValueError(f"unsupported sandbox language: {language!r}")

        import time as _time

        client = self._client()
        name = f"atlas-sbx-{uuid.uuid4().hex[:12]}"
        files = {_LANG_FILE[language]: code, **(extra_files or {})}
        start = _time.perf_counter()

        container = client.containers.create(
            image=self._settings.sandbox_image,
            command=_LANG_CMD[language],
            name=name,
            network_mode=self._settings.sandbox_network,
            mem_limit=self._settings.sandbox_memory_limit,
            memswap_limit=self._settings.sandbox_memory_limit,
            nano_cpus=self._nano_cpus(),
            pids_limit=128,
            read_only=True,
            tmpfs={"/workspace": "rw,size=64m,exec", "/tmp": "rw,size=32m"},
            working_dir="/workspace",
            user="1000:1000",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            environment={"HOME": "/workspace", "PYTHONDONTWRITEBYTECODE": "1"},
            detach=True,
        )
        try:
            container.put_archive("/workspace", _tar_bytes(files))
            container.start()
            timed_out = False
            try:
                exit_status = container.wait(timeout=self._settings.sandbox_timeout_seconds)
                exit_code = int(exit_status.get("StatusCode", 1))
            except Exception:
                timed_out = True
                exit_code = 124
                container.kill()

            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", "replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", "replace")
            duration_ms = int((_time.perf_counter() - start) * 1000)
            log.info(
                "sandbox_run",
                language=language,
                exit_code=exit_code,
                timed_out=timed_out,
                duration_ms=duration_ms,
            )
            return SandboxResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                timed_out=timed_out,
                duration_ms=duration_ms,
            )
        finally:
            try:
                container.remove(force=True)
            except Exception:  # best-effort cleanup
                log.warning("sandbox_cleanup_failed", container=name)


def _tar_bytes(files: dict[str, str]) -> bytes:
    """Pack ``files`` into an in-memory tar for ``put_archive``."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for path, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=path)
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    buf.seek(0)
    return buf.read()
