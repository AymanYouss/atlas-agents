"""Fetch and extract readable text from a URL."""

from __future__ import annotations

import re
from typing import Any

import httpx

from atlas.tools.base import SourceRef, Tool, ToolResult, ToolSpec

_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_HTML_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\n\s*\n\s*\n+")


class HttpFetchTool(Tool):
    def __init__(self, *, max_chars: int = 12000) -> None:
        self._max_chars = max_chars
        self.spec = ToolSpec(
            name="http_fetch",
            description=(
                "Fetch a single web page by URL and return its readable text "
                "content. Use after web_search to read a promising source in full."
            ),
            produces_citations=True,
            input_schema={
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Absolute http(s) URL."}},
                "required": ["url"],
            },
        )

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        url = str(arguments.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            return ToolResult.failure("http_fetch requires an absolute http(s) 'url'")
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "AtlasAgent/0.4"})
            resp.raise_for_status()
            html = resp.text
        text = _extract_text(html)[: self._max_chars]
        title = _title(html) or url
        return ToolResult(
            ok=True,
            content=text,
            data={"url": url, "title": title, "chars": len(text)},
            sources=[SourceRef(title=title, url=url, snippet=text[:300])],
        )


def _extract_text(html: str) -> str:
    without_code = _TAG_RE.sub(" ", html)
    text = _HTML_RE.sub(" ", without_code)
    text = re.sub(r"[ \t]+", " ", text)
    return _WS_RE.sub("\n\n", text).strip()


def _title(html: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None
