"""Run API routes."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from atlas.api.deps import get_run_manager
from atlas.api.schemas import (
    CreateRunRequest,
    RunDetail,
    RunListResponse,
    RunSummary,
    SubmitApprovalsRequest,
)
from atlas.observability.events import EventType, event_broker
from atlas.schemas.run import RunConfig
from atlas.service.run_manager import RunManager

router = APIRouter(prefix="/api", tags=["runs"])


@router.post("/runs", response_model=RunDetail, status_code=201)
async def create_run(
    body: CreateRunRequest, manager: RunManager = Depends(get_run_manager)
) -> RunDetail:
    config = RunConfig(auto_approve=body.auto_approve, max_steps=body.max_steps, tags=body.tags)
    record = await manager.create_run(body.goal, config=config, tags=body.tags)
    manager.launch(record.id, record.goal, config)
    return RunDetail.from_record(record)


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    limit: int = 50, offset: int = 0, manager: RunManager = Depends(get_run_manager)
) -> RunListResponse:
    limit = max(1, min(limit, 200))
    runs = await manager.list_runs(limit=limit, offset=offset)
    return RunListResponse(
        runs=[RunSummary.from_record(r) for r in runs], limit=limit, offset=offset
    )


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(run_id: str, manager: RunManager = Depends(get_run_manager)) -> RunDetail:
    record = await manager.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run not found")
    return RunDetail.from_record(record)


@router.post("/runs/{run_id}/approvals", response_model=RunDetail)
async def submit_approvals(
    run_id: str,
    body: SubmitApprovalsRequest,
    manager: RunManager = Depends(get_run_manager),
) -> RunDetail:
    record = await manager.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run not found")
    decisions = {sid: d.model_dump() for sid, d in body.decisions.items()}
    updated = await manager.submit_approval(run_id, decisions)
    return RunDetail.from_record(updated or record)


@router.get("/runs/{run_id}/events")
async def stream_events(
    run_id: str, request: Request, manager: RunManager = Depends(get_run_manager)
) -> EventSourceResponse:
    """Server-Sent Events: durable replay from Postgres, then live events.

    Reconnecting clients pass ``Last-Event-ID``; only newer events are replayed,
    so a dropped connection resumes without duplicating the timeline.
    """
    record = await manager.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run not found")

    last_id = int(request.headers.get("last-event-id", 0) or 0)

    async def event_source() -> AsyncIterator[dict]:
        # 1) Durable replay of everything already persisted.
        for ev in await manager.replay_events(run_id, after_seq=last_id):
            yield {
                "id": str(ev.seq),
                "event": ev.type,
                "data": json.dumps(
                    {"step_id": ev.step_id, "agent": ev.agent, "payload": ev.payload}
                ),
            }
        # 2) Live tail from the broker (replay=False to avoid duplicating step 1).
        async for live in event_broker.subscribe(run_id, replay=False):
            if await request.is_disconnected():
                break
            if live.seq <= last_id:
                continue
            yield {
                "id": str(live.seq),
                "event": str(live.type),
                "data": json.dumps(
                    {"step_id": live.step_id, "agent": live.agent, "payload": live.payload}
                ),
            }
            if live.type in {EventType.REPORT_READY, EventType.ERROR}:
                # Give the client a moment, then stop the stream for terminal runs.
                await asyncio.sleep(0.1)
                break

    return EventSourceResponse(event_source())
