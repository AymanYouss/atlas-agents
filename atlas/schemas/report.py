"""The final, citation-backed report returned to the caller."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A single source backing a claim in the report."""

    marker: str = Field(description="Inline marker used in the report body, e.g. '[1]'.")
    source: str = Field(description="Tool or step that produced the evidence.")
    title: str = Field(default="", description="Human-readable title of the source.")
    url: str | None = Field(default=None, description="URL when the source is a web page.")
    snippet: str = Field(default="", description="The exact quoted evidence supporting the claim.")


class Report(BaseModel):
    """The synthesized answer with inline citations."""

    summary: str = Field(description="One-paragraph executive answer to the goal.")
    body_markdown: str = Field(description="Full report in Markdown with inline citation markers.")
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Critic-assigned confidence that the report satisfies the goal.",
    )

    @property
    def citation_count(self) -> int:
        return len(self.citations)
