"""End-to-end tests of the orchestration graph using the deterministic FakeLLM.

These exercise the full planner -> execute -> critique -> synthesize loop, a
critic-triggered retry, and a human-in-the-loop approval gate — entirely
in-process, with no network, LLM, Postgres or Docker.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from atlas.agents.schemas import ExecutorAction, PlannerOutput, PlannerStep, ToolCallRequest
from atlas.graph.orchestrator import Orchestrator
from atlas.llm.base import AgentRole
from atlas.schemas.run import Critique, RunConfig, RunStatus
from atlas.tools.base import Tool, ToolResult, ToolSpec
from tests.conftest import FakeLLM


class _NotesTool(Tool):
    def __init__(self) -> None:
        self.spec = ToolSpec(
            name="notes", description="return canned research notes", produces_citations=True
        )

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        from atlas.tools.base import SourceRef

        return ToolResult(
            ok=True,
            content="Paris is the capital of France.",
            sources=[
                SourceRef(title="Geography 101", url="https://example.com/fr", snippet="Paris")
            ],
        )


def _registry():
    from atlas.tools.registry import ToolRegistry

    r = ToolRegistry()
    r.register(_NotesTool())
    return r


def _plan_two_steps(*, gated: bool = False) -> PlannerOutput:
    return PlannerOutput(
        rationale="search then synthesize",
        steps=[
            PlannerStep(id="step-1", title="research", allowed_tools=["notes"]),
            PlannerStep(
                id="step-2",
                title="write up",
                depends_on=["step-1"],
                requires_approval=gated,
            ),
        ],
    )


def _passing_critique(target: str) -> Critique:
    return Critique(target=target, passed=True, score=0.9, retry_recommended=False)


def _make_llm(
    actions: list[ExecutorAction], critiques: list[Critique], plan: PlannerOutput, report_text: str
) -> FakeLLM:
    llm = FakeLLM()
    llm.set_structured(PlannerOutput, plan)
    llm.set_structured(ExecutorAction, list(actions))
    llm.set_structured(Critique, list(critiques))
    llm.completions = [report_text]
    return llm


@pytest.fixture
def orchestrator() -> Orchestrator:
    return Orchestrator()


async def _run(orchestrator: Orchestrator, llm: FakeLLM, tmp_path: Path, **kw) -> dict:
    llms = dict.fromkeys((AgentRole.PLANNER, AgentRole.EXECUTOR, AgentRole.CRITIC), llm)
    return await orchestrator.start(
        run_id=kw.pop("run_id", "run-test"),
        goal="What is the capital of France?",
        config=kw.pop("config", RunConfig(auto_approve=True)),
        registry=_registry(),
        workspace=tmp_path / "ws",
        llms=llms,
        **kw,
    )


async def test_happy_path_completes_with_report(orchestrator: Orchestrator, tmp_path: Path) -> None:
    llm = _make_llm(
        actions=[
            ExecutorAction(thought="look it up", tool_call=ToolCallRequest(tool="notes")),
            ExecutorAction(
                thought="done", final_answer="Paris is the capital [1]", citation_markers=["[1]"]
            ),
            ExecutorAction(
                thought="synthesize",
                final_answer="Paris, per research [1]",
                citation_markers=["[1]"],
            ),
        ],
        critiques=[
            _passing_critique("step-1"),
            _passing_critique("step-2"),
            _passing_critique("report"),
        ],
        plan=_plan_two_steps(),
        report_text="Paris is the capital of France.\n\nParis is the capital [1].",
    )
    state = await _run(orchestrator, llm, tmp_path)
    assert state["status"] == RunStatus.COMPLETED
    assert state["report"] is not None
    assert state["report"]["summary"]
    assert set(state["completed"]) == {"step-1", "step-2"}


async def test_tool_invocation_recorded(orchestrator: Orchestrator, tmp_path: Path) -> None:
    llm = _make_llm(
        actions=[
            ExecutorAction(thought="look it up", tool_call=ToolCallRequest(tool="notes")),
            ExecutorAction(thought="done", final_answer="answer [1]", citation_markers=["[1]"]),
            ExecutorAction(thought="synthesize", final_answer="final [1]"),
        ],
        critiques=[
            _passing_critique("step-1"),
            _passing_critique("step-2"),
            _passing_critique("report"),
        ],
        plan=_plan_two_steps(),
        report_text="Summary.\n\nBody with source [1].",
    )
    state = await _run(orchestrator, llm, tmp_path)
    step1 = state["results"]["step-1"]
    assert any(inv["tool"] == "notes" and inv["ok"] for inv in step1["tool_invocations"])
    # The source gathered by the tool becomes a citation in the report.
    assert state["report"]["citations"], "expected at least one citation from the tool source"


async def test_critic_triggers_retry(orchestrator: Orchestrator, tmp_path: Path) -> None:
    llm = _make_llm(
        actions=[
            ExecutorAction(thought="first attempt", final_answer="weak answer"),
            ExecutorAction(
                thought="second attempt", final_answer="strong answer [1]", citation_markers=["[1]"]
            ),
            ExecutorAction(thought="synthesize", final_answer="final"),
        ],
        critiques=[
            Critique(
                target="step-1",
                passed=False,
                score=0.3,
                retry_recommended=True,
                suggestions=["add a citation"],
            ),
            _passing_critique("step-1"),
            _passing_critique("step-2"),
            _passing_critique("report"),
        ],
        plan=PlannerOutput(
            rationale="single step",
            steps=[
                PlannerStep(id="step-1", title="answer"),
                PlannerStep(id="step-2", title="wrap", depends_on=["step-1"]),
            ],
        ),
        report_text="Summary.\n\nBody.",
    )
    state = await _run(orchestrator, llm, tmp_path, run_id="run-retry")
    assert state["status"] == RunStatus.COMPLETED
    # step-1 should have been attempted twice.
    assert state["results"]["step-1"]["attempt"] == 2


async def test_approval_gate_pauses_and_resumes(orchestrator: Orchestrator, tmp_path: Path) -> None:
    llm = _make_llm(
        actions=[
            ExecutorAction(thought="research", tool_call=ToolCallRequest(tool="notes")),
            ExecutorAction(thought="done", final_answer="researched [1]", citation_markers=["[1]"]),
            ExecutorAction(thought="gated step", final_answer="approved work done"),
        ],
        critiques=[
            _passing_critique("step-1"),
            _passing_critique("step-2"),
            _passing_critique("report"),
        ],
        plan=_plan_two_steps(gated=True),
        report_text="Summary.\n\nBody [1].",
    )
    llms = dict.fromkeys((AgentRole.PLANNER, AgentRole.EXECUTOR, AgentRole.CRITIC), llm)
    paused = await orchestrator.start(
        run_id="run-approval",
        goal="do a sensitive thing",
        config=RunConfig(auto_approve=False),
        registry=_registry(),
        workspace=tmp_path / "ws",
        llms=llms,
    )
    approvals = orchestrator.pending_approvals(paused)
    assert approvals, "expected an approval request while paused"
    assert approvals[0]["step_id"] == "step-2"

    resumed = await orchestrator.resume(
        run_id="run-approval",
        decisions={"step-2": {"decision": "approved"}},
    )
    assert resumed["status"] == RunStatus.COMPLETED
    assert "step-2" in resumed["completed"]
