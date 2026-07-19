"""Web search tool backed by the Tavily API.

Tavily is the reference provider because it returns clean, snippet-level results
that map directly onto Atlas citations. Any other search backend can be dropped
in by implementing the same :class:`Tool` interface, or by attaching an MCP
search server, without touching the executor.
"""

from __future__ import annotations

from typing import Any

import httpx

from atlas.config import Settings, get_settings
from atlas.tools.base import SourceRef, Tool, ToolResult, ToolSpec

_TAVILY_URL = "https://api.tavily.com/search"


class WebSearchTool(Tool):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self.spec = ToolSpec(
            name="web_search",
            description=(
                "Search the public web for up-to-date information. Returns ranked "
                "results with titles, URLs and content snippets that can be cited."
            ),
            produces_citations=True,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        )

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        query = str(arguments.get("query", "")).strip()
        if not query:
            return ToolResult.failure("web_search requires a non-empty 'query'")
        max_results = int(arguments.get("max_results", 5))
        if not self._settings.tavily_api_key:
            return ToolResult.failure("TAVILY_API_KEY is not configured")

        payload = {
            "api_key": self._settings.tavily_api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
            "include_answer": True,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(_TAVILY_URL, json=payload)
            resp.raise_for_status()
            body = resp.json()

        results = body.get("results", [])
        sources = [
            SourceRef(
                title=r.get("title", ""),
                url=r.get("url"),
                snippet=(r.get("content", "") or "")[:500],
            )
            for r in results
        ]
        lines = [f"Search results for {query!r}:"]
        if body.get("answer"):
            lines.append(f"\nSynthesized answer: {body['answer']}")
        for i, s in enumerate(sources, start=1):
            lines.append(f"\n[{i}] {s.title}\n    {s.url}\n    {s.snippet}")
        return ToolResult(
            ok=True,
            content="\n".join(lines),
            data={"answer": body.get("answer"), "results": results},
            sources=sources,
        )
