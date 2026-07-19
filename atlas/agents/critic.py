"""The critic: independent verification of step results and the final report."""

from __future__ import annotations

from atlas.agents.prompts import CRITIC_SYSTEM
from atlas.llm.base import LLMClient, LLMMessage
from atlas.observability.logging import get_logger
from atlas.schemas.plan import PlanStep
from atlas.schemas.report import Report
from atlas.schemas.run import Critique, StepResult

log = get_logger("atlas.critic")


class Critic:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def review_step(self, step: PlanStep, result: StepResult, goal: str) -> Critique:
        tool_summary = (
            "\n".join(f"- {inv.tool}: ok={inv.ok}" for inv in result.tool_invocations)
            or "(no tools used)"
        )
        messages = [
            LLMMessage(role="system", content=CRITIC_SYSTEM),
            LLMMessage(
                role="user",
                content=(
                    f"Overall goal:\n{goal}\n\n"
                    f"Step under review ({step.id}): {step.title}\n"
                    f"Objective:\n{step.detail or step.title}\n\n"
                    f"Tools used:\n{tool_summary}\n\n"
                    f"Step output:\n{result.output}\n\n"
                    "Judge whether this step met its objective. Target should be "
                    f"the step id {step.id!r}."
                ),
            ),
        ]
        critique = await self._llm.structured(messages, Critique, temperature=0.0)
        critique.target = step.id
        log.info("step_critiqued", step=step.id, passed=critique.passed, score=critique.score)
        return critique

    async def review_report(self, report: Report, goal: str) -> Critique:
        messages = [
            LLMMessage(role="system", content=CRITIC_SYSTEM),
            LLMMessage(
                role="user",
                content=(
                    f"Goal:\n{goal}\n\n"
                    f"Proposed final report:\n{report.body_markdown}\n\n"
                    f"Citations provided: {report.citation_count}\n\n"
                    "Judge whether the report fully and accurately answers the goal "
                    "with adequate citations. Target should be 'report'."
                ),
            ),
        ]
        critique = await self._llm.structured(messages, Critique, temperature=0.0)
        critique.target = "report"
        log.info("report_critiqued", passed=critique.passed, score=critique.score)
        return critique
