"""The evaluation harness.

What separates Atlas from a notebook demo: a repeatable benchmark suite that
scores end-to-end task success, plus adversarial suites that measure
prompt-injection resistance and runaway-loop containment. The harness runs every
task through the real orchestrator and aggregates task-success rate, citation
coverage, step/token cost and safety metrics.
"""

from atlas.eval.report import SuiteReport, TaskOutcome
from atlas.eval.runner import EvalRunner
from atlas.eval.suite import BenchmarkTask, Suite, load_suite

__all__ = [
    "BenchmarkTask",
    "EvalRunner",
    "Suite",
    "SuiteReport",
    "TaskOutcome",
    "load_suite",
]
