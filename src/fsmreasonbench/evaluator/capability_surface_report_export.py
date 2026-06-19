"""Export paper-ready reports from capability-surface combined summaries."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any

from fsmreasonbench.evaluator.io import load_json

_METRIC_FIELDS = (
    "extractability_rate",
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
)

_CSV_AGG_FIELDS = (
    "family",
    "model",
    "n_levels",
    "missing_level_count",
    *_METRIC_FIELDS,
)

_INTERPRETATION_TEMPLATE = (
    "This report summarizes an **exploratory** capability-surface run. Metrics are "
    "averaged across recorded difficulty levels per family and model. Where verdict "
    "accuracy exceeds certificate validity, the pattern is consistent with the "
    "benchmark's verdict-overstatement hypothesis — but no final claims should be "
    "drawn from non-frozen, in-progress cohorts. Treat all values as diagnostic "
    "only until a frozen public cohort is evaluated."
)


@dataclass(frozen=True, slots=True)
class CombinedSummary:
    """Normalized capability-surface combined summary."""

    rows: tuple[dict[str, Any], ...]
    families: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    source_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CompletenessReport:
    """Missing family × level × model cells relative to inferred grid."""

    expected_cells: int
    present_cells: int
    missing_cells: tuple[tuple[str, int, str], ...]

    @property
    def missing_count(self) -> int:
        return len(self.missing_cells)


@dataclass(frozen=True, slots=True)
class FamilyModelAggregate:
    """Mean metrics for one family/model pair across difficulty levels."""

    family: str
    model: str
    n_levels: int
    missing_level_count: int
    extractability_rate: float
    verdict_accuracy: float
    certificate_valid_rate: float
    fully_correct_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "model": self.model,
            "n_levels": self.n_levels,
            "missing_level_count": self.missing_level_count,
            "extractability_rate": self.extractability_rate,
            "verdict_accuracy": self.verdict_accuracy,
            "certificate_valid_rate": self.certificate_valid_rate,
            "fully_correct_rate": self.fully_correct_rate,
        }


@dataclass(frozen=True, slots=True)
class FamilyAggregate:
    """Mean metrics pooled across models and levels for one family."""

    family: str
    n_rows: int
    extractability_rate: float
    verdict_accuracy: float
    certificate_valid_rate: float
    fully_correct_rate: float


def load_combined_summary(path: str | Path) -> CombinedSummary:
    """Load ``combined_summary.json`` or ``combined_summary.csv``."""
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(resolved)

    if resolved.suffix.lower() == ".csv":
        return _load_combined_summary_csv(resolved)
    return _load_combined_summary_json(resolved)


def _load_combined_summary_json(path: Path) -> CombinedSummary:
    payload = load_json(path)
    if isinstance(payload, list):
        rows = tuple(_normalize_row(row) for row in payload)
        metadata: dict[str, Any] = {}
    elif isinstance(payload, dict):
        raw_rows = payload.get("rows", [])
        if not isinstance(raw_rows, list):
            raise ValueError("combined_summary.json must contain a 'rows' list")
        rows = tuple(_normalize_row(row) for row in raw_rows)
        metadata = {
            key: payload[key]
            for key in ("n_per_level", "seed", "temperature")
            if key in payload
        }
    else:
        raise ValueError("combined_summary.json must be an object or list")

    families = _coerce_str_tuple(payload.get("families") if isinstance(payload, dict) else None, rows, "family")
    models = _coerce_str_tuple(payload.get("models") if isinstance(payload, dict) else None, rows, "model")
    return CombinedSummary(
        rows=rows,
        families=families,
        models=models,
        source_path=str(path),
        metadata=metadata,
    )


def _load_combined_summary_csv(path: Path) -> CombinedSummary:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("combined_summary.csv is empty")
        for raw in reader:
            rows.append(_normalize_row(raw))
    row_tuple = tuple(rows)
    return CombinedSummary(
        rows=row_tuple,
        families=_coerce_str_tuple(None, row_tuple, "family"),
        models=_coerce_str_tuple(None, row_tuple, "model"),
        source_path=str(path),
    )


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    required = {"family", "difficulty_level", "model", *_METRIC_FIELDS}
    missing = required - row.keys()
    if missing:
        raise ValueError(f"summary row missing fields: {sorted(missing)}")

    normalized = dict(row)
    normalized["family"] = str(row["family"])
    normalized["model"] = str(row["model"])
    normalized["difficulty_level"] = int(row["difficulty_level"])
    for metric in _METRIC_FIELDS:
        normalized[metric] = float(row[metric])
    return normalized


def _coerce_str_tuple(
    declared: Any,
    rows: tuple[dict[str, Any], ...],
    key: str,
) -> tuple[str, ...]:
    if isinstance(declared, list) and declared:
        return tuple(str(value) for value in declared)
    return tuple(dict.fromkeys(str(row[key]) for row in rows))


def analyze_completeness(summary: CombinedSummary) -> CompletenessReport:
    """Infer expected grid and list missing family/level/model cells."""
    if not summary.families or not summary.models:
        present = len(summary.rows)
        return CompletenessReport(expected_cells=present, present_cells=present, missing_cells=())

    levels_by_family: dict[str, list[int]] = {}
    for family in summary.families:
        levels = sorted(
            {
                row["difficulty_level"]
                for row in summary.rows
                if row["family"] == family
            }
        )
        levels_by_family[family] = levels

    present_keys = {
        (row["family"], row["difficulty_level"], row["model"]) for row in summary.rows
    }
    missing: list[tuple[str, int, str]] = []
    expected = 0
    for family in summary.families:
        levels = levels_by_family.get(family, [])
        if not levels:
            continue
        for level in levels:
            for model in summary.models:
                expected += 1
                key = (family, level, model)
                if key not in present_keys:
                    missing.append(key)

    return CompletenessReport(
        expected_cells=expected,
        present_cells=len(present_keys),
        missing_cells=tuple(sorted(missing)),
    )


def aggregate_by_family_model(
    summary: CombinedSummary,
    *,
    completeness: CompletenessReport | None = None,
) -> list[FamilyModelAggregate]:
    """Average metrics per family/model across recorded difficulty levels."""
    del completeness  # reserved for future strict diagnostics
    levels_by_family: dict[str, set[int]] = defaultdict(set)
    for row in summary.rows:
        levels_by_family[row["family"]].add(row["difficulty_level"])

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in summary.rows:
        grouped[(row["family"], row["model"])].append(row)

    pairs: set[tuple[str, str]] = set(grouped.keys())
    if summary.families and summary.models:
        for family in summary.families:
            for model in summary.models:
                pairs.add((family, model))

    aggregates: list[FamilyModelAggregate] = []
    for family, model in sorted(pairs):
        bucket = grouped.get((family, model), [])
        expected_levels = levels_by_family.get(family, set())
        present_levels = {row["difficulty_level"] for row in bucket}
        missing_count = len(expected_levels - present_levels)

        if bucket:
            aggregates.append(
                FamilyModelAggregate(
                    family=family,
                    model=model,
                    n_levels=len(bucket),
                    missing_level_count=missing_count,
                    extractability_rate=mean(row["extractability_rate"] for row in bucket),
                    verdict_accuracy=mean(row["verdict_accuracy"] for row in bucket),
                    certificate_valid_rate=mean(row["certificate_valid_rate"] for row in bucket),
                    fully_correct_rate=mean(row["fully_correct_rate"] for row in bucket),
                )
            )
        else:
            aggregates.append(
                FamilyModelAggregate(
                    family=family,
                    model=model,
                    n_levels=0,
                    missing_level_count=len(expected_levels),
                    extractability_rate=float("nan"),
                    verdict_accuracy=float("nan"),
                    certificate_valid_rate=float("nan"),
                    fully_correct_rate=float("nan"),
                )
            )
    return aggregates


def aggregate_by_family(summary: CombinedSummary) -> list[FamilyAggregate]:
    """Average metrics per family across all rows."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in summary.rows:
        grouped[row["family"]].append(row)

    aggregates: list[FamilyAggregate] = []
    for family in sorted(grouped):
        bucket = grouped[family]
        aggregates.append(
            FamilyAggregate(
                family=family,
                n_rows=len(bucket),
                extractability_rate=mean(row["extractability_rate"] for row in bucket),
                verdict_accuracy=mean(row["verdict_accuracy"] for row in bucket),
                certificate_valid_rate=mean(row["certificate_valid_rate"] for row in bucket),
                fully_correct_rate=mean(row["fully_correct_rate"] for row in bucket),
            )
        )
    return aggregates


def render_capability_surface_report_markdown(
    summary: CombinedSummary,
    *,
    completeness: CompletenessReport | None = None,
    family_model: list[FamilyModelAggregate] | None = None,
    by_family: list[FamilyAggregate] | None = None,
) -> str:
    """Render Markdown report grouped by family."""
    completeness = completeness or analyze_completeness(summary)
    family_model = family_model or aggregate_by_family_model(summary, completeness=completeness)
    by_family = by_family or aggregate_by_family(summary)

    lines = [
        "# Capability Surface Report (exploratory)",
        "",
        f"Source: `{summary.source_path}`",
        f"Rows recorded: {len(summary.rows)}",
        f"Grid completeness: {completeness.present_cells}/{completeness.expected_cells} cells",
    ]
    if completeness.missing_count:
        lines.append(f"Missing cells: {completeness.missing_count}")
    lines.extend(["", "## Family averages", ""])
    lines.extend(
        [
            "| Family | Rows | Extractability | Verdict | Certificate | Fully correct |",
            "|--------|-----:|---------------:|--------:|------------:|--------------:|",
        ]
    )
    for agg in by_family:
        lines.append(
            f"| {agg.family} | {agg.n_rows} | "
            f"{agg.extractability_rate:.3f} | {agg.verdict_accuracy:.3f} | "
            f"{agg.certificate_valid_rate:.3f} | {agg.fully_correct_rate:.3f} |"
        )

    for family in summary.families or sorted({agg.family for agg in family_model}):
        family_rows = [agg for agg in family_model if agg.family == family]
        if not family_rows:
            continue
        lines.extend(["", f"## {family} — model comparison", ""])
        lines.extend(
            [
                "| Model | Levels | Missing levels | Extractability | Verdict | Certificate | Fully correct |",
                "|-------|-------:|---------------:|---------------:|--------:|------------:|--------------:|",
            ]
        )
        for agg in family_rows:
            lines.append(
                f"| `{agg.model}` | {agg.n_levels} | {agg.missing_level_count} | "
                f"{_fmt_metric(agg.extractability_rate)} | {_fmt_metric(agg.verdict_accuracy)} | "
                f"{_fmt_metric(agg.certificate_valid_rate)} | {_fmt_metric(agg.fully_correct_rate)} |"
            )

        level_rows = [row for row in summary.rows if row["family"] == family]
        if level_rows:
            lines.extend(["", f"### {family} — by difficulty level", ""])
            lines.extend(
                [
                    "| Model | Level | Extractability | Verdict | Certificate | Fully correct |",
                    "|-------|------:|---------------:|--------:|------------:|--------------:|",
                ]
            )
            for row in sorted(level_rows, key=lambda r: (r["model"], r["difficulty_level"])):
                lines.append(
                    f"| `{row['model']}` | {row['difficulty_level']} | "
                    f"{row['extractability_rate']:.3f} | {row['verdict_accuracy']:.3f} | "
                    f"{row['certificate_valid_rate']:.3f} | {row['fully_correct_rate']:.3f} |"
                )

    if completeness.missing_count:
        lines.extend(["", "## Missing cells", ""])
        lines.append("| Family | Level | Model |")
        lines.append("|--------|------:|-------|")
        for family, level, model in completeness.missing_cells:
            lines.append(f"| {family} | {level} | `{model}` |")

    lines.extend(["", "## Interpretation (template)", "", _INTERPRETATION_TEMPLATE, ""])
    return "\n".join(lines).rstrip() + "\n"


def render_capability_surface_latex_table(
    family_model: list[FamilyModelAggregate],
    *,
    caption: str | None = None,
    label: str = "tab:capability-surface-summary",
) -> str:
    """Render LaTeX table with mean metrics per family/model."""
    cap = caption or (
        "Capability surface summary (exploratory; means over recorded difficulty levels)."
    )
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        f"\\caption{{{_latex_text(cap)}}}",
        f"\\label{{{label}}}",
        "\\begin{tabular}{llrrrr}",
        "\\toprule",
        "Family & Model & Extract. & Verdict & Cert. & Full \\\\",
        "\\midrule",
    ]
    current_family: str | None = None
    for agg in sorted(family_model, key=lambda row: (row.family, row.model)):
        if current_family is not None and agg.family != current_family:
            lines.append("\\midrule")
        current_family = agg.family
        lines.append(
            f"{_latex_text(agg.family)} & {_latex_text(agg.model)} & "
            f"{_fmt_latex_metric(agg.extractability_rate)} & "
            f"{_fmt_latex_metric(agg.verdict_accuracy)} & "
            f"{_fmt_latex_metric(agg.certificate_valid_rate)} & "
            f"{_fmt_latex_metric(agg.fully_correct_rate)} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    return "\n".join(lines)


def write_aggregated_csv(path: str | Path, family_model: list[FamilyModelAggregate]) -> Path:
    """Write aggregated family/model means to CSV."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_AGG_FIELDS)
        writer.writeheader()
        for agg in family_model:
            writer.writerow(
                {
                    "family": agg.family,
                    "model": agg.model,
                    "n_levels": agg.n_levels,
                    "missing_level_count": agg.missing_level_count,
                    "extractability_rate": _fmt_metric(agg.extractability_rate),
                    "verdict_accuracy": _fmt_metric(agg.verdict_accuracy),
                    "certificate_valid_rate": _fmt_metric(agg.certificate_valid_rate),
                    "fully_correct_rate": _fmt_metric(agg.fully_correct_rate),
                }
            )
    return out_path


def export_capability_surface_report(
    summary_path: str | Path,
    *,
    out_md: str | Path | None = None,
    out_tex: str | Path | None = None,
    out_csv: str | Path | None = None,
    strict: bool = False,
) -> dict[str, Path]:
    """Load summary and write Markdown, LaTeX, and optional CSV exports."""
    summary = load_combined_summary(summary_path)
    completeness = analyze_completeness(summary)
    if strict and completeness.missing_count:
        raise ValueError(
            f"incomplete summary: {completeness.missing_count} missing cells "
            f"({completeness.present_cells}/{completeness.expected_cells} present)"
        )

    family_model = aggregate_by_family_model(summary, completeness=completeness)
    by_family = aggregate_by_family(summary)
    written: dict[str, Path] = {}

    if out_md is not None:
        md_path = Path(out_md)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(
            render_capability_surface_report_markdown(
                summary,
                completeness=completeness,
                family_model=family_model,
                by_family=by_family,
            ),
            encoding="utf-8",
        )
        written["markdown"] = md_path

    if out_tex is not None:
        tex_path = Path(out_tex)
        tex_path.parent.mkdir(parents=True, exist_ok=True)
        tex_path.write_text(
            render_capability_surface_latex_table(family_model),
            encoding="utf-8",
        )
        written["latex"] = tex_path

    if out_csv is not None:
        written["csv"] = write_aggregated_csv(out_csv, family_model)

    return written


def _fmt_metric(value: float) -> str:
    if value != value:  # NaN
        return "—"
    return f"{value:.3f}"


def _fmt_latex_metric(value: float) -> str:
    if value != value:
        return "---"
    return f"{value:.3f}"


_LATEX_ESCAPES = {
    "\\": "\\textbackslash{}",
    "&": "\\&",
    "%": "\\%",
    "$": "\\$",
    "#": "\\#",
    "_": "\\_",
    "{": "\\{",
    "}": "\\}",
    "~": "\\textasciitilde{}",
    "^": "\\textasciicircum{}",
}


def _latex_text(value: str) -> str:
    escaped = value
    for char, replacement in _LATEX_ESCAPES.items():
        escaped = escaped.replace(char, replacement)
    return escaped
