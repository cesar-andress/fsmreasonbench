"""Shared ACM-friendly figure styling for TOSEM manuscript exports."""

from __future__ import annotations

from typing import Any

VERDICT_BAR_COLOR = "0.78"
FULL_BAR_COLOR = "0.25"
STAGE_BAR_COLORS: tuple[str, ...] = ("0.75", "0.45", "0.10")


def configure_paper_figure_style() -> None:
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "text.color": "black",
            "axes.labelcolor": "black",
            "xtick.color": "black",
            "ytick.color": "black",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.size": 9,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }
    )


def style_axes(ax: Any) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_verdict_full_pairs(
    ax: Any,
    *,
    categories: list[tuple[str, str]],
    verdict_rates: list[float | None],
    full_rates: list[float | None],
    category_labels: list[str] | None = None,
    title: str | None = None,
    show_legend: bool = False,
    bar_width: float = 0.34,
) -> None:
    """Grouped verdict vs full bars for one model panel."""
    labels = category_labels or [f"{family}/{track}" for family, track in categories]
    x = list(range(len(labels)))
    offsets_verdict = [pos - bar_width / 2 for pos in x]
    offsets_full = [pos + bar_width / 2 for pos in x]

    ax.bar(
        offsets_verdict,
        [0.0 if rate is None else rate for rate in verdict_rates],
        width=bar_width,
        label="Verdict accuracy",
        color=VERDICT_BAR_COLOR,
        edgecolor="0.0",
        linewidth=0.6,
    )
    ax.bar(
        offsets_full,
        [0.0 if rate is None else rate for rate in full_rates],
        width=bar_width,
        label="Full correctness",
        color=FULL_BAR_COLOR,
        edgecolor="0.0",
        linewidth=0.6,
    )
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("Rate")
    if title:
        ax.set_title(title)
    style_axes(ax)
    if show_legend:
        ax.legend(loc="upper right", frameon=False)
