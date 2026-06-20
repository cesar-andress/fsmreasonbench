"""Compare R0/R1/R2 LLM track run summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.tracks.delegation import DELEGATION_GAP_METRICS, compute_delegation_gap

TRACK_COMPARISON_FIELDS: tuple[str, ...] = (
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
    "delegation_gap_R1_minus_R0_verdict_accuracy",
    "delegation_gap_R1_minus_R0_certificate_valid_rate",
    "delegation_gap_R1_minus_R0_fully_correct_rate",
    "delegation_gap_R2_minus_R0_verdict_accuracy",
    "delegation_gap_R2_minus_R0_certificate_valid_rate",
    "delegation_gap_R2_minus_R0_fully_correct_rate",
)


def _load_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"summary not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "track" not in payload:
        payload["track"] = payload.get("track", "R0")
    return payload


def _resolve_summary(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    for name in ("track_summary.json", "summary.json"):
        candidate = root / name
        if candidate.exists():
            return _load_summary(candidate)
    raise FileNotFoundError(f"no summary.json or track_summary.json under {root}")


def build_track_comparison(
    *,
    r0_dir: str | Path,
    r1_dir: str | Path,
    r2_dir: str | Path,
) -> dict[str, Any]:
    r0 = _resolve_summary(r0_dir)
    r1 = _resolve_summary(r1_dir)
    r2 = _resolve_summary(r2_dir)

    r0["track"] = "R0"
    r1["track"] = "R1"
    r2["track"] = "R2"

    gap_r1 = compute_delegation_gap(r0, r1)
    gap_r2 = compute_delegation_gap(r0, r2)

    row = {
        "track": "comparison",
        "model": r0.get("model") or r1.get("model") or r2.get("model"),
        "family": r0.get("family"),
        "n": r0.get("n"),
        "extractability_rate": None,
        "verdict_accuracy": None,
        "certificate_valid_rate": None,
        "fully_correct_rate": None,
        "tool_invocation_rate": None,
        "average_tool_calls_per_item": None,
    }
    for metric in DELEGATION_GAP_METRICS:
        row[f"delegation_gap_R1_minus_R0_{metric}"] = gap_r1["delegation_gap"][metric]
        row[f"delegation_gap_R2_minus_R0_{metric}"] = gap_r2["delegation_gap"][metric]

    return {
        "track_summaries": [r0, r1, r2],
        "delegation_gaps": {
            "R1_minus_R0": gap_r1,
            "R2_minus_R0": gap_r2,
        },
        "comparison_row": row,
    }


def write_track_comparison_csv(path: str | Path, track_summaries: list[dict[str, Any]]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        for summary in track_summaries:
            writer.writerow(
                {
                    "track": summary.get("track"),
                    "model": summary.get("model"),
                    "family": summary.get("family"),
                    "n": summary.get("n"),
                    "extractability_rate": summary.get("extractability_rate"),
                    "verdict_accuracy": summary.get("verdict_accuracy"),
                    "certificate_valid_rate": summary.get("certificate_valid_rate"),
                    "fully_correct_rate": summary.get("fully_correct_rate"),
                    "tool_invocation_rate": summary.get("tool_invocation_rate", 0.0),
                    "average_tool_calls_per_item": summary.get(
                        "average_tool_calls_per_item", 0.0
                    ),
                }
            )


def render_track_comparison_markdown(payload: dict[str, Any]) -> str:
    summaries = payload["track_summaries"]
    gaps = payload["delegation_gaps"]
    lines = [
        "# Track Comparison Report",
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
) -> dict[str, Path]:
    payload = build_track_comparison(r0_dir=r0_dir, r1_dir=r1_dir, r2_dir=r2_dir)
    json_path = Path(out_json)
    csv_path = Path(out_csv)
    md_path = Path(out_md)
    dump_json(json_path, payload)
    write_track_comparison_csv(csv_path, payload["track_summaries"])
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_track_comparison_markdown(payload), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "md": md_path}
