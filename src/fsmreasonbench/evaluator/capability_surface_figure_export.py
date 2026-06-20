"""Export publication-ready capability-surface figures."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

_LEVEL_SECTION_RE = re.compile(r"^###\s+(C2|F1)\s+—\s+by difficulty level\s*$", re.MULTILINE)
_LEVEL_ROW_RE = re.compile(
    r"^\|\s*`?([^|`]+)`?\s*\|\s*(\d+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*$"
)

_DEFAULT_REPORT_BY_SUMMARY = {
    "capability_surface_summary.csv": "capability_surface_report.md",
    "f1_mixed_capability_surface_summary.csv": "f1_mixed_capability_surface_report.md",
}

_GRAYSCALE_SERIES_STYLES: tuple[dict[str, str], ...] = (
    {"color": "0.0", "marker": "o", "linestyle": "-"},
    {"color": "0.35", "marker": "s", "linestyle": "--"},
    {"color": "0.55", "marker": "^", "linestyle": "-."},
    {"color": "0.75", "marker": "D", "linestyle": ":"},
)


@dataclass(frozen=True, slots=True)
class LevelMetricRow:
    """Per-model/per-level capability-surface metrics."""

    family: str
    model: str
    difficulty_level: int
    extractability_rate: float
    verdict_accuracy: float
    certificate_valid_rate: float
    fully_correct_rate: float
    fully_correct_rate_ci_low: float | None = None
    fully_correct_rate_ci_high: float | None = None


def infer_report_path(summary_csv: str | Path) -> Path:
    """Infer paired Markdown report path from summary CSV filename."""
    summary_csv = Path(summary_csv)
    companion = _DEFAULT_REPORT_BY_SUMMARY.get(summary_csv.name)
    if companion is None:
        raise ValueError(
            f"no default report mapping for {summary_csv.name}; pass --report-md explicitly"
        )
    return summary_csv.parent / companion


def load_summary_models(summary_csv: str | Path, *, family: str) -> list[str]:
    """Load model identifiers for one family from an aggregate summary CSV."""
    summary_csv = Path(summary_csv)
    models: list[str] = []
    with summary_csv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["family"] == family:
                models.append(row["model"])
    if not models:
        raise ValueError(f"no rows for family {family!r} in {summary_csv}")
    return models


def parse_level_metrics_from_report_md(
    report_path: str | Path,
    *,
    family: str,
) -> list[LevelMetricRow]:
    """Parse the per-level markdown table for one family."""
    text = Path(report_path).read_text(encoding="utf-8")
    return parse_level_metrics_from_report_text(text, family=family)


def parse_level_metrics_from_report_text(
    text: str,
    *,
    family: str,
) -> list[LevelMetricRow]:
    """Parse the per-level markdown table for one family from report text."""
    section = _extract_level_section(text, family=family)
    rows: list[LevelMetricRow] = []
    for line in section.splitlines():
        match = _LEVEL_ROW_RE.match(line.strip())
        if not match:
            continue
        model, level, extractability, verdict, certificate, fully_correct = match.groups()
        rows.append(
            LevelMetricRow(
                family=family,
                model=model.strip(),
                difficulty_level=int(level),
                extractability_rate=float(extractability),
                verdict_accuracy=float(verdict),
                certificate_valid_rate=float(certificate),
                fully_correct_rate=float(fully_correct),
            )
        )
    if not rows:
        raise ValueError(f"no per-level rows found for family {family!r}")
    return rows


def merge_json_confidence_intervals(
    rows: list[LevelMetricRow],
    summary_json: str | Path,
    *,
    family: str,
) -> list[LevelMetricRow]:
    """Attach bootstrap CI fields from combined_summary.json when present."""
    import json

    payload = json.loads(Path(summary_json).read_text(encoding="utf-8"))
    indexed = {
        (row["family"], row["difficulty_level"], row["model"]): row for row in payload["rows"]
    }
    merged: list[LevelMetricRow] = []
    for row in rows:
        source = indexed.get((family, row.difficulty_level, row.model))
        if source is None:
            merged.append(row)
            continue
        merged.append(
            LevelMetricRow(
                family=row.family,
                model=row.model,
                difficulty_level=row.difficulty_level,
                extractability_rate=row.extractability_rate,
                verdict_accuracy=row.verdict_accuracy,
                certificate_valid_rate=row.certificate_valid_rate,
                fully_correct_rate=row.fully_correct_rate,
                fully_correct_rate_ci_low=source.get("fully_correct_rate_ci_low"),
                fully_correct_rate_ci_high=source.get("fully_correct_rate_ci_high"),
            )
        )
    return merged


def render_capability_surface_figure(
    rows: list[LevelMetricRow],
    out_path: str | Path,
    *,
    family: str,
    title: str | None = None,
) -> Path:
    """Render a grayscale-friendly LaTeX-ready PDF line plot."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib import rcParams
    except ImportError as exc:
        raise RuntimeError(
            "figure export requires matplotlib; install with: pip install 'fsmreasonbench[plot]'"
        ) from exc

    rcParams.update(
        {
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.size": 9,
            "axes.labelsize": 9,
            "legend.fontsize": 7.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }
    )

    family_rows = [row for row in rows if row.family == family]
    if not family_rows:
        raise ValueError(f"no rows for family {family!r}")

    models = sorted({row.model for row in family_rows}, key=_model_sort_key)
    levels = sorted({row.difficulty_level for row in family_rows})
    indexed = {(row.model, row.difficulty_level): row for row in family_rows}

    figure, axis = plt.subplots(figsize=(3.4, 2.5))
    for index, model in enumerate(models):
        style = _GRAYSCALE_SERIES_STYLES[index % len(_GRAYSCALE_SERIES_STYLES)]
        x_values = [level for level in levels if (model, level) in indexed]
        y_values = [indexed[(model, level)].fully_correct_rate for level in x_values]
        line = axis.plot(x_values, y_values, label=model, **style)
        lows = [
            indexed[(model, level)].fully_correct_rate_ci_low
            for level in x_values
            if indexed[(model, level)].fully_correct_rate_ci_low is not None
        ]
        highs = [
            indexed[(model, level)].fully_correct_rate_ci_high
            for level in x_values
            if indexed[(model, level)].fully_correct_rate_ci_high is not None
        ]
        if lows and highs and len(lows) == len(x_values) and len(highs) == len(x_values):
            axis.fill_between(
                x_values,
                lows,
                highs,
                color=line[0].get_color(),
                alpha=0.15,
                linewidth=0,
            )

    axis.set_title(title or f"{family} fully correct rate (exploratory)")
    axis.set_xlabel("Difficulty level")
    axis.set_ylabel("Fully correct rate")
    axis.set_xticks(levels)
    axis.set_ylim(0.0, 1.05)
    axis.grid(True, alpha=0.25, color="0.7")
    axis.legend(frameon=False, loc="best")
    figure.tight_layout()

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out_path, format="pdf", bbox_inches="tight")
    plt.close(figure)
    return out_path


def export_capability_surface_figure(
    summary_csv: str | Path,
    out_path: str | Path,
    *,
    family: str,
    report_md: str | Path | None = None,
    summary_json: str | Path | None = None,
    title: str | None = None,
) -> Path:
    """Export one capability-surface PDF figure from summary CSV + paired report."""
    summary_csv = Path(summary_csv)
    report_md = Path(report_md) if report_md is not None else infer_report_path(summary_csv)

    expected_models = load_summary_models(summary_csv, family=family)
    rows = parse_level_metrics_from_report_md(report_md, family=family)
    parsed_models = sorted({row.model for row in rows}, key=_model_sort_key)
    if parsed_models != sorted(expected_models, key=_model_sort_key):
        raise ValueError(
            "model mismatch between summary CSV and report markdown: "
            f"csv={expected_models}, report={parsed_models}"
        )

    if summary_json is not None:
        rows = merge_json_confidence_intervals(rows, summary_json, family=family)

    return render_capability_surface_figure(rows, out_path, family=family, title=title)


def _extract_level_section(text: str, *, family: str) -> str:
    matches = list(_LEVEL_SECTION_RE.finditer(text))
    for match in matches:
        if match.group(1) != family:
            continue
        start = match.end()
        tail = text[start:]
        if "\n### " in tail:
            tail = tail.split("\n### ", maxsplit=1)[0]
        if "\n## " in tail:
            tail = tail.split("\n## ", maxsplit=1)[0]
        return tail
    raise ValueError(f"missing per-level section for family {family!r}")


def _model_sort_key(model: str) -> tuple[str, ...]:
    return tuple(part.lower() for part in model.replace(":", "_").split("_"))
