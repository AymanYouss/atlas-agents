"""The planner: goal + available tools -> validated Plan."""

from __future__ import annotations

from atlas.agents.prompts import PLANNER_SYSTEM, render_tool_catalog
from atlas.agents.schemas import PlannerOutput
from atlas.llm.base import LLMClient, LLMMessage
from atlas.observability.logging import get_logger
from atlas.schemas.plan import Plan, PlanStep
from atlas.tools.base import ToolSpec

log = get_logger("atlas.planner")


class Planner:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def plan(self, goal: str, tools: list[ToolSpec]) -> Plan:
        tool_names = {t.name for t in tools}
        messages = [
            LLMMessage(role="system", content=PLANNER_SYSTEM),
            LLMMessage(
                role="user",
                content=(
                    f"Goal:\n{goal}\n\n"
                    f"Available tools:\n{render_tool_catalog(tools)}\n\n"
                    "Produce the plan."
                ),
            ),
        ]
        raw: PlannerOutput = await self._llm.structured(messages, PlannerOutput, temperature=0.0)

        steps: list[PlanStep] = []
        for s in raw.steps:
            allowed = [t for t in s.allowed_tools if t in tool_names]
            steps.append(
                PlanStep(
                    id=s.id,
                    title=s.title,
                    detail=s.detail,
                    depends_on=s.depends_on,
                    allowed_tools=allowed,
                    requires_approval=s.requires_approval,
                )
            )
        plan = Plan(goal=goal, rationale=raw.rationale, steps=steps)
        log.info("plan_created", goal=goal, steps=len(plan.steps))
        return plan
