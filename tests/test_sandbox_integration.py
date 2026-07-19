"""Integration tests for the Docker sandbox.

Marked ``integration`` and skipped automatically when the Docker daemon or the
sandbox image is unavailable, so the unit suite stays hermetic.
"""

from __future__ import annotations

import pytest

from atlas.sandbox.docker_sandbox import DockerSandbox, SandboxUnavailableError

pytestmark = pytest.mark.integration


def _sandbox_or_skip() -> DockerSandbox:
    sb = DockerSandbox()
    try:
        client = sb._client()
    except SandboxUnavailableError:
        pytest.skip("Docker daemon not available")
    try:
        client.images.get(sb._settings.sandbox_image)
    except Exception:
        pytest.skip(f"sandbox image {sb._settings.sandbox_image!r} not built")
    return sb


def test_python_hello() -> None:
    sb = _sandbox_or_skip()
    result = sb.run("print('hello from sandbox')", language="python")
    assert result.ok
    assert "hello from sandbox" in result.stdout


def test_network_is_disabled() -> None:
    sb = _sandbox_or_skip()
    code = (
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
        "    print('NETWORK_REACHABLE')\n"
        "except OSError:\n"
        "    print('NETWORK_BLOCKED')\n"
    )
    result = sb.run(code, language="python")
    assert "NETWORK_BLOCKED" in result.stdout


def test_wall_clock_timeout() -> None:
    sb = _sandbox_or_skip()
    result = sb.run("import time\nwhile True: time.sleep(1)", language="python")
    assert result.timed_out
    assert result.exit_code == 124
