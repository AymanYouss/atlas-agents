"""Assemble the LangGraph state machine."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from atlas.graph.context import context_table
from atlas.graph.nodes import (
    execute_node,
    finalize_node,
    plan_node,
    replan_node,
    synthesize_node,
)
from atlas.graph.state import AtlasState
from atlas.schemas.plan import Plan


def _route_after_execute(
    state: AtlasState,
) -> Literal["execute", "synthesize", "replan", "finalize"]:
    if state.get("error"):
        return "finalize"

    plan = Plan.model_validate(state["plan"])
    completed = set(state.get("completed", []))
    failed = set(state.get("failed", []))
    done = completed | failed

    if len(done) >= len(plan.steps):
        return "synthesize"

    ready_exists = any(s.id not in done and set(s.depends_on) <= completed for s in plan.steps)
    if ready_exists:
        return "execute"

    # Remaining steps are blocked by failures. Replan if we still have budget.
    max_replans = context_table.get(state["run_id"]).max_replans
    if state.get("replans", 0) < max_replans:
        return "replan"
    return "synthesize"


def build_graph(checkpointer: Any | None = None):
    """Compile the Atlas orchestration graph, optionally with a checkpointer."""
    graph: StateGraph = StateGraph(AtlasState)
    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("replan", replan_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "execute")
    graph.add_conditional_edges(
        "execute",
        _route_after_execute,
        {
            "execute": "execute",
            "replan": "replan",
            "synthesize": "synthesize",
            "finalize": "finalize",
        },
    )
    graph.add_edge("replan", "execute")
    graph.add_edge("synthesize", END)
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=checkpointer)
