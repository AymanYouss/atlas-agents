from __future__ import annotations

import pytest

from atlas.config import Settings
from atlas.tools.builtin.web_search import WebSearchTool


@pytest.fixture
def settings() -> Settings:
    return Settings(TAVILY_API_KEY="tvly-test")


async def test_web_search_parses_results_into_sources(httpx_mock, settings: Settings) -> None:
    httpx_mock.add_response(
        url="https://api.tavily.com/search",
        json={
            "answer": "Paris is the capital of France.",
            "results": [
                {
                    "title": "France - Wikipedia",
                    "url": "https://en.wikipedia.org/wiki/France",
                    "content": "France's capital is Paris.",
                },
                {
                    "title": "Paris",
                    "url": "https://example.com/paris",
                    "content": "Paris is a city.",
                },
            ],
        },
    )
    tool = WebSearchTool(settings=settings)
    result = await tool.invoke({"query": "capital of France", "max_results": 2})
    assert result.ok
    assert len(result.sources) == 2
    assert result.sources[0].url == "https://en.wikipedia.org/wiki/France"
    assert "Paris" in result.content


async def test_web_search_requires_query(settings: Settings) -> None:
    tool = WebSearchTool(settings=settings)
    result = await tool.invoke({"query": "   "})
    assert result.ok is False


async def test_web_search_requires_api_key() -> None:
    tool = WebSearchTool(settings=Settings(TAVILY_API_KEY=None))
    result = await tool.invoke({"query": "anything"})
    assert result.ok is False
    assert "TAVILY_API_KEY" in (result.error or "")
