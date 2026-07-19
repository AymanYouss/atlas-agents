"""Render the benchmark results as a portfolio-quality chart.

Reads docs/benchmarks/results.json (the output of `atlas eval run --all --out`)
and produces a dark, control-plane-styled figure:

  * task-success rate by category (core suite)
  * headline metrics and injection-defense summary

Usage: python scripts/plot_benchmarks.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "docs" / "benchmarks" / "results.json"
OUT = ROOT / "docs" / "portfolio" / "03-eval-scores.png"

# Palette mirrors the web UI control-plane theme.
BG = "#0A0A0B"
SURFACE = "#111114"
BORDER = "#26262B"
TEXT = "#E4E4E7"
MUTED = "#A1A1AA"
CYAN = "#22D3EE"
AMBER = "#F59E0B"
GREEN = "#34D399"

MONO = next(
    (f for f in ["JetBrains Mono", "DejaVu Sans Mono", "Menlo", "Courier New"]
     if any(f in n for n in (fnt.name for fnt in fm.fontManager.ttflist))),
    "monospace",
)


def _load() -> tuple[dict, dict]:
    data = json.loads(RESULTS.read_text())
    core = next(s for s in data if s["suite"] == "core")
    injection = next(s for s in data if s["suite"] == "injection")
    return core, injection


def main() -> None:
    core, injection = _load()
    plt.rcParams.update(
        {
            "font.family": MONO,
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "savefig.facecolor": BG,
            "text.color": TEXT,
            "axes.labelcolor": TEXT,
            "xtick.color": MUTED,
            "ytick.color": TEXT,
        }
    )

    fig = plt.figure(figsize=(12, 7.0), dpi=200)
    fig.text(
        0.062,
        0.945,
        "Atlas  ·  benchmark suite results",
        ha="left",
        fontsize=18,
        color=TEXT,
        fontweight="bold",
    )
    fig.text(
        0.062,
        0.895,
        "task success by category (core suite)   ·   adversarial injection defense",
        ha="left",
        fontsize=11,
        color=MUTED,
    )

    # ---- Left: success rate by category (horizontal bars) -------------------
    ax = fig.add_axes([0.062, 0.12, 0.55, 0.66])
    cats = core["by_category"]
    order = sorted(cats.items(), key=lambda kv: kv[1]["success_rate"])
    labels = [c for c, _ in order]
    rates = [v["success_rate"] * 100 for _, v in order]
    totals = [v["total"] for _, v in order]

    ax.barh(labels, [100] * len(labels), color=SURFACE, edgecolor=BORDER, height=0.6)
    bars = ax.barh(labels, rates, color=CYAN, height=0.6)
    for bar, rate, total in zip(bars, rates, totals, strict=True):
        ax.text(
            min(rate + 2.5, 92),
            bar.get_y() + bar.get_height() / 2,
            f"{rate:.0f}%  ({total})",
            va="center",
            ha="left",
            color=TEXT,
            fontsize=10.5,
        )
    ax.set_xlim(0, 100)
    ax.set_xlabel("success rate", fontsize=10)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="x", color=BORDER, linewidth=0.6, alpha=0.6)
    ax.set_axisbelow(True)

    # ---- Right: headline stat cards -----------------------------------------
    def card(x, y, w, h, value, label, accent):
        ax2 = fig.add_axes([x, y, w, h])
        ax2.set_axis_off()
        box = FancyBboxPatch(
            (0.02, 0.05),
            0.96,
            0.9,
            boxstyle="round,pad=0.02,rounding_size=0.06",
            linewidth=1,
            edgecolor=BORDER,
            facecolor=SURFACE,
            transform=ax2.transAxes,
        )
        ax2.add_patch(box)
        ax2.text(0.1, 0.60, value, fontsize=26, color=accent, fontweight="bold",
                 transform=ax2.transAxes)
        ax2.text(0.1, 0.26, label, fontsize=10.5, color=MUTED, transform=ax2.transAxes)

    core_sr = core["success_rate"] * 100
    card(0.66, 0.55, 0.30, 0.26, f"{core_sr:.0f}%", "core task success", CYAN)
    card(
        0.66,
        0.24,
        0.30,
        0.26,
        f"{injection['passed']}/{injection['total']}",
        f"injection attempts contained · {injection['blocked_injections']} quarantined",
        GREEN,
    )
    fig.text(
        0.66,
        0.15,
        f"mean score {core['mean_score']:.2f}   ·   ~{core['mean_latency_ms'] / 1000:.1f}s / task",
        fontsize=9.5,
        color=MUTED,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight", pad_inches=0.3)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
