from __future__ import annotations

import pytest

from atlas.schemas import Plan, PlanStep
from atlas.schemas.plan import StepStatus
from atlas.schemas.report import Citation, Report


def _plan() -> Plan:
    return Plan(
        goal="research and summarize",
        steps=[
            PlanStep(id="s1", title="search", allowed_tools=["web_search"]),
            PlanStep(id="s2", title="read", depends_on=["s1"]),
            PlanStep(id="s3", title="synthesize", depends_on=["s1", "s2"]),
        ],
    )


def test_ready_steps_respects_dependencies() -> None:
    plan = _plan()
    assert [s.id for s in plan.ready_steps(set())] == ["s1"]
    assert [s.id for s in plan.ready_steps({"s1"})] == ["s2"]
    assert [s.id for s in plan.ready_steps({"s1", "s2"})] == ["s3"]


def test_ready_steps_excludes_completed() -> None:
    plan = _plan()
    assert plan.ready_steps({"s1", "s2", "s3"}) == []


def test_completed_step_status_not_reoffered() -> None:
    plan = _plan()
    plan.step("s1").status = StepStatus.SUCCEEDED
    assert "s1" not in {s.id for s in plan.ready_steps({"s1"})}


def test_unknown_dependency_rejected() -> None:
    with pytest.raises(ValueError, match="unknown step"):
        Plan(goal="g", steps=[PlanStep(id="a", title="a", depends_on=["ghost"])])


def test_cycle_rejected() -> None:
    with pytest.raises(ValueError, match="cycle"):
        Plan(
            goal="g",
            steps=[
                PlanStep(id="a", title="a", depends_on=["b"]),
                PlanStep(id="b", title="b", depends_on=["a"]),
            ],
        )


def test_duplicate_ids_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        Plan(goal="g", steps=[PlanStep(id="a", title="a"), PlanStep(id="a", title="b")])


def test_self_dependency_rejected() -> None:
    with pytest.raises(ValueError, match="cannot depend on itself"):
        PlanStep(id="a", title="a", depends_on=["a"])


def test_report_citation_count() -> None:
    report = Report(
        summary="s",
        body_markdown="body [1]",
        citations=[Citation(marker="[1]", source="web_search", title="t")],
        confidence=0.8,
    )
    assert report.citation_count == 1
    assert 0.0 <= report.confidence <= 1.0
