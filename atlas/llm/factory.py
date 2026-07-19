"""Resolve an :class:`LLMClient` for a given agent role from settings."""

from __future__ import annotations

from functools import cache

from atlas.config import Settings, get_settings
from atlas.llm.base import AgentRole, LLMClient
from atlas.llm.providers import AnthropicClient, OpenAIClient


def _model_for(role: AgentRole, settings: Settings) -> str:
    return {
        AgentRole.PLANNER: settings.planner_model,
        AgentRole.EXECUTOR: settings.executor_model,
        AgentRole.CRITIC: settings.critic_model,
    }[role]


@cache
def _cached_client(role: AgentRole, provider: str, model: str) -> LLMClient:
    settings = get_settings()
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set; cannot construct an Anthropic client."
            )
        return AnthropicClient(model, role, settings.anthropic_api_key)
    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set; cannot construct an OpenAI client.")
        return OpenAIClient(model, role, settings.openai_api_key)
    raise ValueError(f"unknown LLM provider: {provider!r}")


def get_llm(role: AgentRole, *, settings: Settings | None = None) -> LLMClient:
    """Return the configured client for ``role``.

    Planner and critic default to the stronger reasoning model; the executor to a
    faster one. Clients are cached per (role, provider, model) so we reuse HTTP
    connection pools across steps.
    """
    settings = settings or get_settings()
    return _cached_client(role, settings.llm_provider, _model_for(role, settings))
