"""Prometheus metrics exposed at ``/metrics``."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

RUNS_TOTAL = Counter(
    "atlas_runs_total", "Total runs started, by terminal status.", ["status"]
)
RUN_DURATION = Histogram(
    "atlas_run_duration_seconds",
    "End-to-end run duration.",
    buckets=(1, 5, 15, 30, 60, 120, 300, 600, 900),
)
STEPS_TOTAL = Counter(
    "atlas_steps_total", "Plan steps executed, by outcome.", ["outcome"]
)
TOOL_CALLS_TOTAL = Counter(
    "atlas_tool_calls_total", "Tool invocations, by tool and outcome.", ["tool", "ok"]
)
TOOL_LATENCY = Histogram(
    "atlas_tool_latency_seconds", "Tool call latency, by tool.", ["tool"]
)
GUARDRAIL_BLOCKS = Counter(
    "atlas_guardrail_blocks_total",
    "Actions blocked by a guardrail, by guardrail name.",
    ["guardrail"],
)
ACTIVE_RUNS = Gauge("atlas_active_runs", "Runs currently executing.")
LLM_TOKENS = Counter(
    "atlas_llm_tokens_total", "LLM tokens consumed, by role and kind.", ["role", "kind"]
)
