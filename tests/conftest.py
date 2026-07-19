"""Shared fixtures and lightweight fakes used across the unit test suite.

The unit suite never touches the network, a real LLM, Postgres or Docker. A fake
LLM client returns scripted structured objects and token streams, so the whole
planner-executor-critic loop is exercised deterministically in-process.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import pytest

os.environ.setdefault("ATLAS_ENV", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault(
    "ATLAS_DATABASE_URL", "postgresql+asyncpg://atlas:atlas@localhost:5432/atlas_test"
)

from atlas.llm.base import AgentRole, LLMClient, LLMMessage, LLMResult, TokenUsage


class FakeLLM(LLMClient):
    """Deterministic LLM used in tests.

    ``structured_responses`` maps a schema type to the object it should return;
    ``completions`` is a FIFO queue of plain-text answers. Every call records its
    messages so tests can assert on prompts.
    """

    def __init__(self, role: AgentRole = AgentRole.EXECUTOR) -> None:
        self.role = role
        self.model = "fake-model"
        self.structured_responses: dict[type, Any] = {}
        self.completions: list[str] = []
        self.calls: list[list[LLMMessage]] = []

    def set_structured(self, schema: type, value: Any) -> None:
        self.structured_responses[schema] = value

    async def complete(
        self, messages: list[LLMMessage], *, temperature: float = 0.2, max_tokens: int = 4096
    ) -> LLMResult:
        self.calls.append(messages)
        text = self.completions.pop(0) if self.completions else "ok"
        return LLMResult(text=text, usage=TokenUsage(input_tokens=10, output_tokens=5))

    async def stream(
        self, messages: list[LLMMessage], *, temperature: float = 0.2, max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        self.calls.append(messages)
        text = self.completions.pop(0) if self.completions else "ok"
        for token in text.split(" "):
            yield token + " "

    async def structured(
        self,
        messages: list[LLMMessage],
        schema: type,
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> Any:
        self.calls.append(messages)
        if schema not in self.structured_responses:
            raise AssertionError(f"no scripted structured response for {schema.__name__}")
        value = self.structured_responses[schema]
        return value.pop(0) if isinstance(value, list) else value


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()
