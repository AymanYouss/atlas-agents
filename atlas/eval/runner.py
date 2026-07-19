"""Runs benchmark tasks through the real orchestrator and scores the results."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

from atlas.eval.report import SuiteReport, TaskOutcome
from atlas.eval.scorer import score_report
from atlas.eval.suite import BenchmarkTask, Suite
from atlas.graph.orchestrator import Orchestrator
from atlas.llm.base import AgentRole, LLMClient
from atlas.observability.logging import get_logger
from atlas.schemas.report import Report
from atlas.schemas.run import RunConfig
from atlas.tools.base import SourceRef, Tool, ToolResult, ToolSpec
from atlas.tools.registry import ToolRegistry

log = get_logger("atlas.eval")


class _SeededSearchTool(Tool):
    """A search tool that returns fixed content, used to inject adversarial payloads."""

    def __init__(self, content: str) -> None:
        self._content = content
        self.spec = ToolSpec(
            name="web_search",
            description="Search the web (evaluation harness, returns seeded content).",
            produces_citations=True,
        )

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(
            ok=True,
            content=self._content,
            sources=[SourceRef(title="seeded source", url="https://eval.local/doc", snippet="")],
        )


class EvalRunner:
    def __init__(
        self,
        *,
        llms: dict[AgentRole, LLMClient] | None = None,
        settings=None,
    ) -> None:
        self._llms = llms
        self._settings = settings

    def _registry_for(self, task: BenchmarkTask, workspace: Path) -> ToolRegistry:
        if task.injected_tool_content is not None:
            registry = ToolRegistry()
            registry.register(_SeededSearchTool(task.injected_tool_content))
            return registry
        from atlas.tools.builtin import default_tools

        registry = ToolRegistry()
        registry.register_many(default_tools(workspace=workspace, settings=self._settings))
        return registry

    async def run_task(self, task: BenchmarkTask) -> TaskOutcome:
        orchestrator = Orchestrator(settings=self._settings)
        workspace = Path(tempfile.mkdtemp(prefix=f"atlas-eval-{task.id}-"))
        registry = self._registry_for(task, workspace)
        run_id = f"eval_{task.id}"
        start = time.perf_counter()
        try:
            state = await orchestrator.start(
                run_id=run_id,
                goal=task.goal,
                config=RunConfig(auto_approve=True, tags=["eval", task.category]),
                registry=registry,
                workspace=workspace,
                llms=self._llms,
            )
        except Exception as exc:  # a task crashing counts as a failure, not a harness crash
            log.warning("eval_task_error", task=task.id, error=str(exc))
            return TaskOutcome(
                task_id=task.id,
                category=task.category,
                difficulty=task.difficulty,
                passed=False,
                score=0.0,
                error=str(exc),
            )
        finally:
            orchestrator.release(run_id)

        latency_ms = int((time.perf_counter() - start) * 1000)
        report = (
            Report.model_validate(state["report"])
            if state.get("report")
            else Report(summary="", body_markdown="")
        )
        results = state.get("results", {})
        blocked = sum(
            1
            for r in results.values()
            for inv in r.get("tool_invocations", [])
            if inv.get("blocked_by_guardrail")
        )
        tokens = sum(int(r.get("tokens_used", 0)) for r in results.values())

        scored = score_report(task, report, blocked_injections=blocked)
        return TaskOutcome(
            task_id=task.id,
            category=task.category,
            difficulty=task.difficulty,
            passed=scored.passed,
            score=scored.score,
            breakdown=scored.breakdown,
            steps=len(results),
            tokens=tokens,
            latency_ms=latency_ms,
            citations=report.citation_count,
            blocked_injections=blocked,
            notes=scored.notes,
        )

    async def run_suite(self, suite: Suite) -> SuiteReport:
        report = SuiteReport(suite=suite.name)
        for task in suite.tasks:
            outcome = await self.run_task(task)
            report.outcomes.append(outcome)
            log.info("eval_task_done", task=task.id, passed=outcome.passed, score=outcome.score)
        return report
