"""The provider-agnostic LLM interface used by every agent."""

from __future__ import annotations

import abc
from enum import Enum
from typing import AsyncIterator, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


class AgentRole(str, Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"


class LLMMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


class LLMResult(BaseModel):
    text: str
    usage: TokenUsage = TokenUsage()


class LLMClient(abc.ABC):
    """Minimal surface every provider must implement.

    Deliberately small: a completion call, a token stream for live reasoning, and
    a structured-output call that returns a validated Pydantic model. The planner
    and critic rely on structured output; the executor relies on streaming.
    """

    role: AgentRole
    model: str

    @abc.abstractmethod
    async def complete(
        self, messages: list[LLMMessage], *, temperature: float = 0.2, max_tokens: int = 4096
    ) -> LLMResult:
        ...

    @abc.abstractmethod
    async def stream(
        self, messages: list[LLMMessage], *, temperature: float = 0.2, max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        ...

    @abc.abstractmethod
    async def structured(
        self,
        messages: list[LLMMessage],
        schema: type[TModel],
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> TModel:
        ...
