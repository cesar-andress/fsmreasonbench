"""Compare R0/R1/R2 LLM track run summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.track_failure_taxonomy import TRACK_FAILURE_CLASSES
from fsmreasonbench.tracks.delegation import DELEGATION_GAP_METRICS, compute_delegation_gap

METRIC_FIELDS: tuple[str, ...] = (
    "track",
    "model",
    "family",
    "n",
    "extractability_rate",
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
    "tool_invocation_rate",
    "average_tool_calls_per_item",
)

DELEGATION_FIELDS: tuple[str, ...] = tuple(
    f"delegation_gap_R1_minus_R0_{metric}" for metric in DELEGATION_GAP_METRICS
) + tuple(f"delegation_gap_R2_minus_R0_{metric}" for metric in DELEGATION_GAP_METRICS)

FAILURE_COUNT_FIELDS: tuple[str, ...] = tuple(
    f"count_{label}" for label in TRACK_FAILURE_CLASSES
)


def _load_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"summary not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_summary(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    for name in ("track_summary.json", "summary.json"):
        candidate = root / name
        if candidate.exists():
            return _load_summary(candidate)
    raise FileNotFoundError(f"no summary.json or track_summary.json under {root}")


def _flatten_summary_row(summary: dict[str, Any]) -> dict[str, Any]:
    row = {field: summary.get(field) for field in METRIC_FIELDS}
    counts = summary.get("track_failure_counts", {})
    for label in TRACK_FAILURE_CLASSES:
        row[f"count_{label}"] = counts.get(label, 0)
    return row


def build_track_comparison(
    *,
    r0_dir: str | Path,
    r1_dir: str | Path,
    r2_dir: str | Path,
    cohort_id: str | None = None,
) -> dict[str, Any]:
    r0 = _resolve_summary(r0_dir)
    r1 = _resolve_summary(r1_dir)
    r2 = _resolve_summary(r2_dir)

    r0["track"] = "R0"
    r1["track"] = "R1"
    r2["track"] = "R2"

    gap_r1 = compute_delegation_gap(r0, r1)
    gap_r2 = compute_delegation_gap(r0, r2)

    comparison_row = {
        "track": "comparison",
        "cohort_id": cohort_id,
        "model": r0.get("model") or r1.get("model") or r2.get("model"),
        "family": r0.get("family"),
        "n": r0.get("n"),
    }
    for metric in DELEGATION_GAP_METRICS:
        comparison_row[f"delegation_gap_R1_minus_R0_{metric}"] = gap_r1[
            "delegation_gap"
        ][metric]
        comparison_row[f"delegation_gap_R2_minus_R0_{metric}"] = gap_r2[
            "delegation_gap"
        ][metric]

    payload = {
        "cohort_id": cohort_id,
        "track_summaries": [r0, r1, r2],
        "track_rows": [_flatten_summary_row(s) for s in (r0, r1, r2)],
        "delegation_gaps": {
            "R1_minus_R0": gap_r1,
            "R2_minus_R0": gap_r2,
        },
        "comparison_row": comparison_row,
    }
    return payload


def build_multi_cohort_track_comparison(
    cohorts: list[dict[str, Any]],
) -> dict[str, Any]:
    comparisons = []
    for cohort in cohorts:
        comparisons.append(
            build_track_comparison(
                r0_dir=cohort["r0_dir"],
                r1_dir=cohort["r1_dir"],
                r2_dir=cohort["r2_dir"],
                cohort_id=cohort.get("cohort_id"),
            )
        )
    return {
        "cohorts": comparisons,
        "track_rows": [row for comp in comparisons for row in comp["track_rows"]],
    }


def write_track_comparison_csv(path: str | Path, track_rows: list[dict[str, Any]]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(METRIC_FIELDS) + list(FAILURE_COUNT_FIELDS)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in track_rows:
            writer.writerow(row)


def render_track_comparison_markdown(payload: dict[str, Any]) -> str:
    if "cohorts" in payload:
        sections = [
            render_track_comparison_markdown(cohort)
            for cohort in payload["cohorts"]
        ]
        return "\n\n---\n\n".join(sections)

    summaries = payload["track_summaries"]
    gaps = payload["delegation_gaps"]
    cohort_label = payload.get("cohort_id") or summaries[0].get("family", "")
    lines = [
        f"# Track Comparison Report — {cohort_label}",
        "",
        "Comparison of LLM evaluation runs under R0, R1, and R2.",
        "",
        "## Per-track metrics",
        "",
        "| track | model | family | n | extract | verdict | cert | full | tool_rate | avg_tools |",
        "|-------|-------|--------|--:|--------:|--------:|-----:|-----:|----------:|----------:|",
    ]
    for row in summaries:
        lines.append(
            "| {track} | {model} | {family} | {n} | "
            "{extract:.3f} | {verdict:.3f} | {cert:.3f} | {full:.3f} | "
            "{tool_rate:.3f} | {avg_tools:.1f} |".format(
                track=row.get("track"),
                model=row.get("model", ""),
                family=row.get("family"),
                n=row.get("n"),
                extract=row.get("extractability_rate", 0.0),
                verdict=row.get("verdict_accuracy", 0.0),
                cert=row.get("certificate_valid_rate", 0.0),
                full=row.get("fully_correct_rate", 0.0),
                tool_rate=row.get("tool_invocation_rate", 0.0),
                avg_tools=row.get("average_tool_calls_per_item", 0.0),
            )
        )

    lines.extend(["", "## Track failure taxonomy", ""])
    lines.append("| track | " + " | ".join(TRACK_FAILURE_CLASSES) + " |")
    lines.append("|-------|" + "|".join(["---:"] * len(TRACK_FAILURE_CLASSES)) + "|")
    for row in summaries:
        counts = row.get("track_failure_counts", {})
        lines.append(
            "| {track} | ".format(track=row.get("track"))
            + " | ".join(str(counts.get(label, 0)) for label in TRACK_FAILURE_CLASSES)
            + " |"
        )

    lines.extend(["", "## Delegation gaps", ""])
    for label, gap_payload in gaps.items():
        lines.append(f"### {label}")
        for metric, value in gap_payload["delegation_gap"].items():
            lines.append(f"- `{metric}`: {value:+.3f}")
        lines.append("")

    return "\n".join(lines)


def export_track_comparison(
    *,
    r0_dir: str | Path,
    r1_dir: str | Path,
    r2_dir: str | Path,
    out_json: str | Path = "docs/track_comparison_summary.json",
    out_csv: str | Path = "docs/track_comparison_summary.csv",
    out_md: str | Path = "docs/track_comparison_report.md",
    cohort_id: str | None = None,
) -> dict[str, Path]:
    payload = build_track_comparison(
        r0_dir=r0_dir,
        r1_dir=r1_dir,
        r2_dir=r2_dir,
        cohort_id=cohort_id,
    )
    json_path = Path(out_json)
    csv_path = Path(out_csv)
    md_path = Path(out_md)
    dump_json(json_path, payload)
    write_track_comparison_csv(csv_path, payload["track_rows"])
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_track_comparison_markdown(payload), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "md": md_path}


def export_multi_cohort_track_comparison(
    cohorts: list[dict[str, Any]],
    *,
    out_json: str | Path,
    out_csv: str | Path,
    out_md: str | Path,
) -> dict[str, Path]:
    payload = build_multi_cohort_track_comparison(cohorts)
    json_path = Path(out_json)
    csv_path = Path(out_csv)
    md_path = Path(out_md)
    dump_json(json_path, payload)
    write_track_comparison_csv(csv_path, payload["track_rows"])
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_track_comparison_markdown(payload), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "md": md_path}
