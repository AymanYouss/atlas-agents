"""API tests driving the real app + run manager with a deterministic FakeLLM."""

from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient

from atlas.agents.schemas import ExecutorAction, PlannerOutput, PlannerStep
from atlas.graph.orchestrator import Orchestrator
from atlas.llm.base import AgentRole
from atlas.main import create_app
from atlas.persistence.repository import InMemoryRunRepository
from atlas.schemas.run import Critique, RunStatus
from atlas.service.run_manager import RunManager
from tests.conftest import FakeLLM


def _scripted_llm(*, gated: bool = False) -> FakeLLM:
    llm = FakeLLM()
    llm.set_structured(
        PlannerOutput,
        PlannerOutput(
            rationale="single step",
            steps=[PlannerStep(id="step-1", title="answer the question", requires_approval=gated)],
        ),
    )
    llm.set_structured(
        ExecutorAction,
        [ExecutorAction(thought="answer", final_answer="The answer is 42.")],
    )
    llm.set_structured(
        Critique,
        [
            Critique(target="step-1", passed=True, score=0.95),
            Critique(target="report", passed=True, score=0.95),
        ],
    )
    llm.completions = ["The answer is 42.\n\nThe answer is 42."]
    return llm


def _app_with(llm: FakeLLM):
    app = create_app()
    manager = RunManager(
        Orchestrator(),
        InMemoryRunRepository(),
        llm_override=dict.fromkeys((AgentRole.PLANNER, AgentRole.EXECUTOR, AgentRole.CRITIC), llm),
    )
    app.state.run_manager = manager
    app.state.ready = True
    return app


def _client(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _poll(client: AsyncClient, run_id: str, target: set[str], *, tries: int = 50) -> dict:
    for _ in range(tries):
        resp = await client.get(f"/api/runs/{run_id}")
        body = resp.json()
        if body["status"] in target:
            return body
        await asyncio.sleep(0.02)
    raise AssertionError(f"run {run_id} did not reach {target}; last={body['status']}")


async def test_healthz() -> None:
    app = _app_with(_scripted_llm())
    async with _client(app) as client:
        assert (await client.get("/healthz")).json() == {"status": "ok"}


async def test_create_and_complete_run() -> None:
    app = _app_with(_scripted_llm())
    async with _client(app) as client:
        resp = await client.post("/api/runs", json={"goal": "What is 6x7?", "auto_approve": True})
        assert resp.status_code == 201
        run_id = resp.json()["id"]

        body = await _poll(client, run_id, {RunStatus.COMPLETED, RunStatus.FAILED})
        assert body["status"] == RunStatus.COMPLETED
        assert body["report"]["summary"]
        assert "step-1" in body["results"]


async def test_run_appears_in_list() -> None:
    app = _app_with(_scripted_llm())
    async with _client(app) as client:
        await client.post("/api/runs", json={"goal": "list me", "auto_approve": True})
        listed = (await client.get("/api/runs")).json()
        assert listed["runs"] and listed["runs"][0]["goal"] == "list me"


async def test_events_are_persisted_for_replay() -> None:
    app = _app_with(_scripted_llm())
    async with _client(app) as client:
        run_id = (
            await client.post("/api/runs", json={"goal": "persist events", "auto_approve": True})
        ).json()["id"]
        await _poll(client, run_id, {RunStatus.COMPLETED, RunStatus.FAILED})
        events = await app.state.run_manager.replay_events(run_id)
        types = {e.type for e in events}
        assert "plan_created" in types
        assert "report_ready" in types


async def test_approval_gate_via_api() -> None:
    app = _app_with(_scripted_llm(gated=True))
    async with _client(app) as client:
        run_id = (
            await client.post("/api/runs", json={"goal": "sensitive", "auto_approve": False})
        ).json()["id"]
        paused = await _poll(client, run_id, {RunStatus.AWAITING_APPROVAL})
        assert paused["pending_approvals"], "expected a pending approval"

        resp = await client.post(
            f"/api/runs/{run_id}/approvals",
            json={"decisions": {"step-1": {"decision": "approved"}}},
        )
        assert resp.status_code == 200
        done = await _poll(client, run_id, {RunStatus.COMPLETED, RunStatus.FAILED})
        assert done["status"] == RunStatus.COMPLETED


async def test_get_missing_run_404() -> None:
    app = _app_with(_scripted_llm())
    async with _client(app) as client:
        assert (await client.get("/api/runs/does-not-exist")).status_code == 404
