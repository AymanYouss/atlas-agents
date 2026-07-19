"""Structured-output schemas the agents exchange with the LLM."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolCallRequest(BaseModel):
    tool: str = Field(description="Name of the tool to call; must be in the allow-list.")
    arguments: dict = Field(default_factory=dict)
    reason: str = Field(default="", description="Why this call helps complete the step.")


class ExecutorAction(BaseModel):
    """One turn of the executor's ReAct loop.

    Exactly one of ``tool_call`` or ``final_answer`` should be set. Using
    structured output (rather than a provider's native tool-calling API) keeps the
    executor identical across Anthropic, OpenAI and any future provider.
    """

    thought: str = Field(description="Brief reasoning about what to do next.")
    tool_call: ToolCallRequest | None = None
    final_answer: str | None = Field(
        default=None, description="The step's result, set only when no more tools are needed."
    )
    citation_markers: list[str] = Field(
        default_factory=list,
        description="Markers like '[1]' for sources this step relied on.",
    )


class PlannerOutput(BaseModel):
    """Raw planner output, validated into a :class:`~atlas.schemas.plan.Plan`."""

    rationale: str
    steps: list[PlannerStep]


class PlannerStep(BaseModel):
    id: str
    title: str
    detail: str = ""
    depends_on: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    requires_approval: bool = False


PlannerOutput.model_rebuild()
