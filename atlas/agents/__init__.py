"""The three agent roles: planner, executor, critic (plus report synthesis).

Each agent is a thin, testable object that takes typed input and returns typed
output via the provider-agnostic :class:`~atlas.llm.base.LLMClient`. They hold no
orchestration logic — sequencing, retries and approvals live in
:mod:`atlas.graph`.
"""

from atlas.agents.critic import Critic
from atlas.agents.executor import Executor
from atlas.agents.planner import Planner
from atlas.agents.synthesizer import ReportSynthesizer

__all__ = ["Critic", "Executor", "Planner", "ReportSynthesizer"]
