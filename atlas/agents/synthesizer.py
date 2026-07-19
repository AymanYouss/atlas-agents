"""Report synthesis: turn step outputs + gathered sources into a cited report.

Streams the report body token-by-token (emitting ``AGENT_TOKEN`` events) so the
UI renders the answer as it is written, then attaches the numbered citations that
were actually referenced.
"""

from __future__ import annotations

import re

from atlas.agents.emitter import AgentEmitter, NullEmitter
from atlas.agents.prompts import SYNTHESIZER_SYSTEM
from atlas.llm.base import LLMClient, LLMMessage
from atlas.observability.events import EventType
from atlas.observability.logging import get_logger
from atlas.schemas.report import Citation, Report
from atlas.schemas.run import StepResult

log = get_logger("atlas.synthesizer")
_MARKER_RE = re.compile(r"\[(\d+)\]")


class ReportSynthesizer:
    def __init__(self, llm: LLMClient, *, emitter: AgentEmitter | None = None) -> None:
        self._llm = llm
        self._emit = emitter or NullEmitter()

    async def synthesize(self, goal: str, results: list[StepResult]) -> Report:
        sources = _collect_sources(results)
        numbered = _render_sources(sources)
        step_digest = "\n\n".join(
            f"### {r.step_id}\n{r.output}" for r in results if r.output.strip()
        )

        messages = [
            LLMMessage(role="system", content=SYNTHESIZER_SYSTEM),
            LLMMessage(
                role="user",
                content=(
                    f"Goal:\n{goal}\n\n"
                    f"Numbered sources (cite with the matching [n]):\n{numbered}\n\n"
                    f"Executor step outputs:\n{step_digest}\n\n"
                    "Write the final answer. The FIRST paragraph is a one-paragraph "
                    "executive summary. Then a blank line, then the detailed report. "
                    "Use inline [n] markers for every non-obvious claim."
                ),
            ),
        ]

        body_parts: list[str] = []
        async for token in self._llm.stream(messages, temperature=0.2, max_tokens=2048):
            body_parts.append(token)
            await self._emit.emit(
                EventType.AGENT_TOKEN, agent="synthesizer", payload={"token": token}
            )
        body = "".join(body_parts).strip()

        summary = body.split("\n\n", 1)[0].strip() if body else ""
        used_markers = {int(m) for m in _MARKER_RE.findall(body)}
        citations = [
            Citation(
                marker=f"[{i}]",
                source=src.get("source", "web"),
                title=src.get("title", ""),
                url=src.get("url"),
                snippet=src.get("snippet", ""),
            )
            for i, src in enumerate(sources, start=1)
            if i in used_markers
        ]
        report = Report(summary=summary, body_markdown=body, citations=citations)
        log.info("report_synthesized", citations=len(citations), chars=len(body))
        return report


def _collect_sources(results: list[StepResult]) -> list[dict]:
    seen: set[str] = set()
    sources: list[dict] = []
    for r in results:
        for inv in r.tool_invocations:
            payload = inv.result if isinstance(inv.result, dict) else {}
            for s in payload.get("sources", []) or []:
                key = s.get("url") or s.get("title") or ""
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                sources.append({**s, "source": inv.tool})
    return sources


def _render_sources(sources: list[dict]) -> str:
    if not sources:
        return "(no external sources were gathered)"
    lines = []
    for i, s in enumerate(sources, start=1):
        title = s.get("title") or s.get("url") or "source"
        url = s.get("url") or ""
        lines.append(f"[{i}] {title} {url}".rstrip())
    return "\n".join(lines)
