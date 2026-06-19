"""Plot capability-surface model evaluation summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_METRIC_SPECS = (
    ("fully_correct_rate", "fully_correct_vs_difficulty.png", "Fully correct rate"),
    ("verdict_accuracy", "verdict_vs_difficulty.png", "Verdict accuracy"),
)


def plot_capability_surface(
    summary_path: str | Path,
    out_dir: str | Path | None = None,
) -> list[Path]:
    """
    Plot model capability curves from ``combined_summary.json``.

    Writes one PNG per metric with C2/F1 subplots.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "plotting requires matplotlib; install with: pip install 'fsmreasonbench[plot]'"
        ) from exc

    payload = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = payload["rows"]
    if not rows:
        raise ValueError("summary contains no rows")

    destination = Path(out_dir) if out_dir is not None else Path(summary_path).parent
    destination.mkdir(parents=True, exist_ok=True)

    families = list(dict.fromkeys(row["family"] for row in rows))
    models = list(dict.fromkeys(row["model"] for row in rows))
    indexed = {
        (row["family"], row["difficulty_level"], row["model"]): row for row in rows
    }

    written: list[Path] = []
    for metric, filename, title in _METRIC_SPECS:
        figure, axes = plt.subplots(1, len(families), figsize=(6 * len(families), 4), squeeze=False)
        for axis_index, family in enumerate(families):
            axis = axes[0][axis_index]
            levels = sorted(
                {row["difficulty_level"] for row in rows if row["family"] == family}
            )
            for model in models:
                y_values = []
                x_values = []
                for level in levels:
                    row = indexed.get((family, level, model))
                    if row is None:
                        continue
                    x_values.append(level)
                    y_values.append(row[metric])
                if x_values:
                    axis.plot(x_values, y_values, marker="o", label=model)
            axis.set_title(f"{family} — {title}")
            axis.set_xlabel("Difficulty level")
            axis.set_ylabel(title)
            axis.set_xticks(levels)
            axis.set_ylim(0.0, 1.05)
            axis.grid(True, alpha=0.3)
            axis.legend(fontsize=8)
        figure.tight_layout()
        output_path = destination / filename
        figure.savefig(output_path, dpi=150)
        plt.close(figure)
        written.append(output_path)

    return written
