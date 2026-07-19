"""Benchmark task and suite definitions, loaded from YAML."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class BenchmarkTask(BaseModel):
    id: str
    goal: str
    category: str = "general"
    difficulty: Difficulty = Difficulty.MEDIUM
    # Rule-based success signals.
    expect_keywords: list[str] = Field(default_factory=list)
    keyword_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Fraction of keywords required to pass."
    )
    min_citations: int = 0
    # Adversarial checks.
    adversarial: bool = False
    forbidden: list[str] = Field(
        default_factory=list,
        description="Strings that must NOT appear in the report (e.g. leaked secrets).",
    )
    # If set, the harness seeds this poisoned content into the tool layer.
    injected_tool_content: str | None = None
    # LLM-judge rubric (used when judging is enabled).
    rubric: list[str] = Field(default_factory=list)
    weight: float = 1.0


class Suite(BaseModel):
    name: str
    description: str = ""
    tasks: list[BenchmarkTask]

    def by_category(self) -> dict[str, list[BenchmarkTask]]:
        out: dict[str, list[BenchmarkTask]] = {}
        for t in self.tasks:
            out.setdefault(t.category, []).append(t)
        return out


def load_suite(path: str | Path) -> Suite:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Suite.model_validate(data)


def suites_dir() -> Path:
    return Path(__file__).parent / "suites"
