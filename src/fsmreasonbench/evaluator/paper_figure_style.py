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


def plot_verdict_full_by_models(
    ax: Any,
    *,
    model_labels: list[str],
    verdict_rates: list[float],
    full_rates: list[float],
    title: str | None = None,
    show_legend: bool = False,
    bar_width: float = 0.34,
) -> None:
    """Grouped verdict vs full bars for one frozen cell across models."""
    x = list(range(len(model_labels)))
    offsets_verdict = [pos - bar_width / 2 for pos in x]
    offsets_full = [pos + bar_width / 2 for pos in x]
    ax.bar(
        offsets_verdict,
        verdict_rates,
        width=bar_width,
        label="Verdict accuracy",
        color=VERDICT_BAR_COLOR,
        edgecolor="0.0",
        linewidth=0.6,
    )
    ax.bar(
        offsets_full,
        full_rates,
        width=bar_width,
        label="Full correctness",
        color=FULL_BAR_COLOR,
        edgecolor="0.0",
        linewidth=0.6,
    )
    ax.set_xticks(x, model_labels, rotation=35, ha="right")
    y_max = 1.22 if show_legend else 1.05
    ax.set_ylim(0.0, y_max)
    ax.set_ylabel("Rate")
    if title:
        ax.set_title(title)
    style_axes(ax)
    if show_legend:
        ax.legend(loc="upper right", frameon=False, fontsize=7, bbox_to_anchor=(1.0, 1.0))


def plot_ablation_subtype_panel(
    ax: Any,
    *,
    condition_labels: list[str],
    subtype_labels: list[str],
    cert_rates: list[list[float]],
    title: str | None = None,
    show_legend: bool = True,
    bar_width: float = 0.22,
    ylabel: str = "Witness validity",
    annotate_rates: bool = False,
) -> None:
    """Grouped witness-validity bars by condition and subtype."""
    import numpy as np

    n_conditions = len(condition_labels)
    n_subtypes = len(subtype_labels)
    x = np.arange(n_conditions, dtype=float)
    for index, subtype_label in enumerate(subtype_labels):
        offset = x + (index - (n_subtypes - 1) / 2.0) * bar_width
        rates = [cert_rates[row_index][index] for row_index in range(n_conditions)]
        bars = ax.bar(
            offset,
            rates,
            width=bar_width,
            label=subtype_label,
            color=STAGE_BAR_COLORS[index % len(STAGE_BAR_COLORS)],
            edgecolor="0.0",
            linewidth=0.6,
        )
        if annotate_rates:
            for bar, rate in zip(bars, rates):
                if rate <= 0.001:
                    continue
                label_y = _ablation_bar_label_y(rate, index, n_subtypes)
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    label_y,
                    f"{rate:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=5.5,
                    color="0.25",
                    clip_on=False,
                )
    rotation = 35 if n_conditions > 3 else 25
    ax.set_xticks(x, condition_labels, rotation=rotation, ha="right")
    y_top = 1.05
    if annotate_rates:
        y_top = 1.24
    if title:
        y_top = max(y_top, 1.22)
    ax.set_ylim(0.0, y_top)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, fontsize=8)
    style_axes(ax)
    if show_legend:
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.28 if n_conditions > 3 else -0.24),
            ncol=len(subtype_labels),
            frameon=False,
            fontsize=6.5,
            columnspacing=1.0,
            handlelength=1.0,
        )


def _ablation_bar_label_y(rate: float, subtype_index: int, n_subtypes: int) -> float:
    """Place rate labels above bars without intra-group overlap."""
    base = rate + 0.025
    if rate >= 0.85:
        base += subtype_index * 0.055
    elif rate >= 0.40:
        base += subtype_index * 0.035
    return min(base, 1.20)
