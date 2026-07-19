"""Concrete LLM providers built on LangChain chat models.

Both providers share :class:`_LangChainClient`, which adapts a LangChain
``BaseChatModel`` to the Atlas :class:`LLMClient` interface: message conversion,
retry with exponential backoff, streaming, token accounting, and structured
output via ``with_structured_output``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from atlas.llm.base import AgentRole, LLMClient, LLMMessage, LLMResult, TokenUsage
from atlas.observability.logging import get_logger

log = get_logger("atlas.llm")
TModel = TypeVar("TModel", bound=BaseModel)


class LLMProviderError(RuntimeError):
    """Raised when the underlying provider fails after all retries."""


def _to_lc(messages: list[LLMMessage]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    for m in messages:
        if m.role == "system":
            out.append(SystemMessage(content=m.content))
        elif m.role == "assistant":
            out.append(AIMessage(content=m.content))
        else:
            out.append(HumanMessage(content=m.content))
    return out


def _usage_from(message: BaseMessage) -> TokenUsage:
    meta = getattr(message, "usage_metadata", None) or {}
    return TokenUsage(
        input_tokens=int(meta.get("input_tokens", 0)),
        output_tokens=int(meta.get("output_tokens", 0)),
    )


_RETRY = retry(
    retry=retry_if_exception_type((TimeoutError, ConnectionError, LLMProviderError)),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    stop=stop_after_attempt(4),
    reraise=True,
)


class _LangChainClient(LLMClient):
    def __init__(self, model: BaseChatModel, role: AgentRole, model_name: str) -> None:
        self._model = model
        self.role = role
        self.model = model_name

    @_RETRY
    async def complete(
        self, messages: list[LLMMessage], *, temperature: float = 0.2, max_tokens: int = 4096
    ) -> LLMResult:
        try:
            resp = await self._model.ainvoke(_to_lc(messages))
        except Exception as exc:
            raise LLMProviderError(str(exc)) from exc
        text = resp.content if isinstance(resp.content, str) else str(resp.content)
        return LLMResult(text=text, usage=_usage_from(resp))

    async def stream(
        self, messages: list[LLMMessage], *, temperature: float = 0.2, max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        async for chunk in self._model.astream(_to_lc(messages)):
            content = chunk.content
            if isinstance(content, str) and content:
                yield content

    @_RETRY
    async def structured(
        self,
        messages: list[LLMMessage],
        schema: type[TModel],
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> TModel:
        structured_model = self._model.with_structured_output(schema, include_raw=False)
        try:
            result = await structured_model.ainvoke(_to_lc(messages))
        except Exception as exc:
            raise LLMProviderError(str(exc)) from exc
        if not isinstance(result, schema):
            result = schema.model_validate(result)
        return result


class AnthropicClient(_LangChainClient):
    def __init__(self, model_name: str, role: AgentRole, api_key: str, **kwargs) -> None:
        from langchain_anthropic import ChatAnthropic

        model = ChatAnthropic(
            model=model_name,
            api_key=api_key,
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=kwargs.get("max_tokens", 4096),
            timeout=kwargs.get("timeout", 120),
            max_retries=0,  # retries handled by tenacity for uniform behaviour
        )
        super().__init__(model, role, model_name)


class OpenAIClient(_LangChainClient):
    def __init__(self, model_name: str, role: AgentRole, api_key: str, **kwargs) -> None:
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=kwargs.get("max_tokens", 4096),
            timeout=kwargs.get("timeout", 120),
            max_retries=0,
        )
        super().__init__(model, role, model_name)
