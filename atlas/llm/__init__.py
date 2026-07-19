"""Provider-agnostic LLM access.

The rest of the codebase talks to :class:`~atlas.llm.base.LLMClient`. Concrete
providers (Anthropic, OpenAI) are constructed by :func:`get_llm`, which resolves
the right model for a given agent *role* from settings. Swapping providers is a
one-line config change; no orchestration code needs to know which model runs.
"""

from atlas.llm.base import AgentRole, LLMClient, LLMMessage, TokenUsage
from atlas.llm.factory import get_llm

__all__ = ["AgentRole", "LLMClient", "LLMMessage", "TokenUsage", "get_llm"]
