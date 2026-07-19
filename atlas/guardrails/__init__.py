"""Guardrails: the safety layer between the model and the outside world.

Two independent concerns:

* :mod:`atlas.guardrails.injection` inspects *untrusted* text (tool results,
  fetched web pages) for prompt-injection and data-exfiltration attempts before
  it is ever fed back to an agent, and wraps it so the model treats it as data.
* :mod:`atlas.guardrails.budget` enforces hard ceilings on steps, retries,
  tokens, wall-clock time and repeated identical actions, which is what stops a
  misbehaving run from looping forever or burning unbounded spend.
"""

from atlas.guardrails.budget import (
    BudgetExceededError,
    BudgetKind,
    RunawayLoopError,
    RunBudget,
)
from atlas.guardrails.injection import (
    InjectionScanner,
    InjectionVerdict,
    Severity,
    wrap_untrusted,
)

__all__ = [
    "BudgetExceededError",
    "BudgetKind",
    "InjectionScanner",
    "InjectionVerdict",
    "RunBudget",
    "RunawayLoopError",
    "Severity",
    "wrap_untrusted",
]
