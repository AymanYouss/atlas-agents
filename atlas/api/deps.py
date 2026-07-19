"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from atlas.service.run_manager import RunManager


def get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager
