"""LangGraph node functions.

Each node reads the checkpointed :class:`~atlas.graph.state.AtlasState`, looks up
its non-serializable :class:`~atlas.graph.context.RunContext` by ``run_id``, does
one unit of orchestration, and returns a partial state update. Keeping nodes pure
w.r.t. their inputs is what makes checkpoint/resume correct.
"""

from __future__ import annotations

import asyncio
import uuid

from langgraph.types import interrupt

from atlas.graph.context import RunContext, context_table
from atlas.graph.state import AtlasState
from atlas.guardrails.budget import BudgetExceededError
from atlas.llm.tokens import estimate_tokens
from atlas.observability.events import EventType
from atlas.observability.logging import get_logger
from atlas.observability.metrics import STEPS_TOTAL
from atlas.schemas.plan import Plan, PlanStep, StepStatus
from atlas.schemas.run import RunStatus, StepResult

log = get_logger("atlas.graph")

_CONTEXT_CHARS = 1500


def _ctx(state: AtlasState) -> RunContext:
    return context_table.get(state["run_id"])


async def plan_node(state: AtlasState) -> dict:
    ctx = _ctx(state)
    await ctx.emitter.emit(EventType.RUN_STATUS, payload={"status": RunStatus.PLANNING})
    plan = await ctx.planner.plan(ctx.goal, ctx.registry.specs())
    ctx.budget.charge_tokens(estimate_tokens(plan.model_dump_json()))
    await ctx.emitter.emit(EventType.PLAN_CREATED, payload={"plan": plan.model_dump(mode="json")})
    return {
        "plan": plan.model_dump(mode="json"),
        "completed": [],
        "failed": [],
        "results": state.get("results", {}),
        "critiques": state.get("critiques", []),
        "approvals": state.get("approvals", {}),
        "replans": state.get("replans", 0),
        "status": RunStatus.EXECUTING,
        "error": None,
    }


def _ready(plan: Plan, completed: set[str], failed: set[str]) -> list[PlanStep]:
    return [
        s
        for s in plan.steps
        if s.id not in completed and s.id not in failed and set(s.depends_on) <= completed
    ]


def _context_digest(results: dict[str, dict], completed: set[str]) -> str:
    chunks = []
    for sid in completed:
        r = results.get(sid)
        if r and r.get("output"):
            chunks.append(f"[{sid}] {r['output'][:400]}")
    text = "\n".join(chunks)
    return text[:_CONTEXT_CHARS]


async def execute_node(state: AtlasState) -> dict:
    ctx = _ctx(state)
    plan = Plan.model_validate(state["plan"])
    completed = set(state.get("completed", []))
    failed = set(state.get("failed", []))
    results = dict(state.get("results", {}))
    critiques = list(state.get("critiques", []))
    approvals = dict(state.get("approvals", {}))

    ready = _ready(plan, completed, failed)
    if not ready:
        return {}

    # --- Human-in-the-loop approval gate -------------------------------------
    gated = [
        s
        for s in ready
        if s.requires_approval and not ctx.config.auto_approve and s.id not in approvals
    ]
    if gated:
        requests = [
            {
                "id": uuid.uuid4().hex,
                "step_id": s.id,
                "reason": "Step is flagged as sensitive/irreversible by the planner.",
                "proposed_action": s.detail or s.title,
            }
            for s in gated
        ]
        await ctx.emitter.emit(EventType.APPROVAL_REQUESTED, payload={"approvals": requests})
        # Pauses the graph durably; the API resumes with the decisions.
        decisions = interrupt({"approvals": requests})
        approvals.update(decisions or {})
        await ctx.emitter.emit(EventType.APPROVAL_RESOLVED, payload={"approvals": approvals})

    # Apply approval decisions, dropping rejected steps.
    runnable: list[PlanStep] = []
    for s in ready:
        decision = approvals.get(s.id)
        if decision and decision.get("decision") == "rejected":
            failed.add(s.id)
            results[s.id] = StepResult(
                step_id=s.id, succeeded=False, error="rejected by human reviewer"
            ).model_dump(mode="json")
            await ctx.emitter.emit(
                EventType.STEP_STATUS, step_id=s.id, payload={"status": StepStatus.SKIPPED}
            )
            continue
        if decision and decision.get("decision") == "edited" and decision.get("edited_instruction"):
            s.detail = decision["edited_instruction"]
        runnable.append(s)

    context_digest = _context_digest(results, completed)

    try:
        outcomes = await asyncio.gather(
            *(self_run_step(ctx, plan, s, context_digest) for s in runnable)
        )
    except BudgetExceededError as exc:
        log.warning("run_budget_exceeded", run_id=ctx.run_id, kind=str(exc.kind))
        await ctx.emitter.emit(
            EventType.GUARDRAIL, payload={"guardrail": str(exc.kind), "message": str(exc)}
        )
        return {"status": RunStatus.FAILED, "error": f"budget exceeded: {exc}"}

    for step_id, result, step_critiques, ok in outcomes:
        results[step_id] = result.model_dump(mode="json")
        critiques.extend(c.model_dump(mode="json") for c in step_critiques)
        if ok:
            completed.add(step_id)
            STEPS_TOTAL.labels(outcome="succeeded").inc()
        else:
            failed.add(step_id)
            STEPS_TOTAL.labels(outcome="failed").inc()

    return {
        "completed": sorted(completed),
        "failed": sorted(failed),
        "results": results,
        "critiques": critiques,
        "approvals": approvals,
        "status": RunStatus.EXECUTING,
    }


async def self_run_step(ctx: RunContext, plan: Plan, step: PlanStep, context_digest: str):
    """Run one step with critic-gated retries. Returns (id, result, critiques, ok)."""
    ctx.budget.charge_step()
    await ctx.emitter.emit(
        EventType.STEP_STATUS, step_id=step.id, payload={"status": StepStatus.RUNNING}
    )
    critiques = []
    attempt = 1
    guidance = ""
    max_retries = ctx.budget.max_retries_per_step

    while True:
        executor = ctx.new_executor()
        result = await executor.run_step(
            step, context=context_digest, attempt=attempt, guidance=guidance
        )
        critique = await ctx.critic.review_step(step, result, ctx.goal)
        ctx.budget.charge_tokens(estimate_tokens(critique.model_dump_json()))
        critiques.append(critique)
        await ctx.emitter.emit(
            EventType.CRITIQUE,
            step_id=step.id,
            agent="critic",
            payload={
                "passed": critique.passed,
                "score": critique.score,
                "issues": critique.issues,
                "retry_recommended": critique.retry_recommended,
            },
        )

        ok = result.succeeded and critique.passed
        if ok:
            await ctx.emitter.emit(
                EventType.STEP_STATUS, step_id=step.id, payload={"status": StepStatus.SUCCEEDED}
            )
            return step.id, result, critiques, True

        if critique.retry_recommended and attempt <= max_retries:
            ctx.budget.charge_retry(step.id)
            attempt += 1
            guidance = "; ".join(critique.suggestions) or "; ".join(critique.issues)
            continue

        await ctx.emitter.emit(
            EventType.STEP_STATUS, step_id=step.id, payload={"status": StepStatus.FAILED}
        )
        return step.id, result, critiques, False


async def replan_node(state: AtlasState) -> dict:
    ctx = _ctx(state)
    replans = state.get("replans", 0) + 1
    await ctx.emitter.emit(EventType.RUN_STATUS, payload={"status": RunStatus.REPLANNING})

    results = state.get("results", {})
    accomplished = "\n".join(
        f"- {sid}: {r.get('output', '')[:200]}" for sid, r in results.items() if r.get("succeeded")
    )
    augmented_goal = (
        f"{ctx.goal}\n\nProgress so far (do not redo these):\n{accomplished or '(none)'}\n\n"
        "Some earlier steps failed or got blocked. Produce a revised plan to finish "
        "the goal from here."
    )
    new_plan = await ctx.planner.plan(augmented_goal, ctx.registry.specs())
    prefix = f"r{replans}:"
    for s in new_plan.steps:
        s.id = f"{prefix}{s.id}"
        s.depends_on = [f"{prefix}{d}" for d in s.depends_on]

    await ctx.emitter.emit(
        EventType.PLAN_CREATED,
        payload={"plan": new_plan.model_dump(mode="json"), "replan": replans},
    )
    return {
        "plan": new_plan.model_dump(mode="json"),
        "completed": [],
        "failed": [],
        "replans": replans,
        "status": RunStatus.EXECUTING,
    }


async def synthesize_node(state: AtlasState) -> dict:
    ctx = _ctx(state)
    await ctx.emitter.emit(EventType.RUN_STATUS, payload={"status": RunStatus.CRITIQUING})
    results = [StepResult.model_validate(v) for v in state.get("results", {}).values()]

    report = await ctx.synthesizer.synthesize(ctx.goal, results)
    ctx.budget.charge_tokens(estimate_tokens(report.body_markdown))
    critique = await ctx.critic.review_report(report, ctx.goal)
    report.confidence = critique.score

    critiques = list(state.get("critiques", []))
    critiques.append(critique.model_dump(mode="json"))
    await ctx.emitter.emit(
        EventType.REPORT_READY, payload={"report": report.model_dump(mode="json")}
    )
    await ctx.emitter.emit(EventType.RUN_STATUS, payload={"status": RunStatus.COMPLETED})
    return {
        "report": report.model_dump(mode="json"),
        "critiques": critiques,
        "status": RunStatus.COMPLETED,
    }


async def finalize_node(state: AtlasState) -> dict:
    ctx = _ctx(state)
    error = state.get("error")
    await ctx.emitter.emit(
        EventType.ERROR if error else EventType.RUN_STATUS,
        payload={"status": RunStatus.FAILED, "error": error},
    )
    return {"status": RunStatus.FAILED}
