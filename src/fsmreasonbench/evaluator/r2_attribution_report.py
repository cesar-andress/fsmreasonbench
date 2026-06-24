"""Report generation for F1 R2 attribution ablation (R2A/R2B/R2C)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.failure_taxonomy import (
    analyze_failure_taxonomy,
    format_failure_taxonomy_report,
)
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.runners.cell_failure import SCORES_JSONL
from fsmreasonbench.runners.experiment_cells import RESULTS_JSONL
from fsmreasonbench.runners.r2_attribution_prompts import (
    MODE_CONDITION_IDS,
    R2AttributionMode,
)


def _format_rate(value: Any) -> str:
    if value is None:
        return "—"
    return f"{float(value):.3f}"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_f1_track_rows(baseline_root: Path) -> dict[str, dict[str, Any]]:
    combined = _load_json(baseline_root / "combined_summary.json")
    if not combined:
        return {}
    return {
        row["track"]: row
        for row in combined.get("track_rows", [])
        if row.get("family") == "F1" and row.get("status") == "completed"
    }


def _comparison_row(
    label: str,
    *,
    cert: Any,
    full: Any,
    failure_stages: dict[str, Any] | None = None,
) -> str:
    fs = failure_stages or {}
    stage = (
        f"not_ext={fs.get('not_extractable', 0)}, "
        f"verdict={fs.get('verdict_wrong', 0)}, "
        f"cert={fs.get('certificate_invalid', 0)}, "
        f"ok={fs.get('correct', 0)}"
    )
    return f"| {label} | {_format_rate(cert)} | {_format_rate(full)} | {stage} |"


def _mode_summary_row(mode_dir: Path, mode: R2AttributionMode) -> dict[str, Any] | None:
    summary = _load_json(mode_dir / "summary.json")
    if not summary:
        return None
    return {
        "label": mode.value,
        "condition_id": MODE_CONDITION_IDS[mode],
        "run_dir": str(mode_dir),
        **summary,
    }


def render_r2_attribution_comparison_report(
    *,
    parent_dir: Path,
    mode_summaries: list[dict[str, Any]],
    frozen_tools_root: Path,
    oracle_ablation_root: Path,
) -> str:
    frozen = _load_f1_track_rows(frozen_tools_root)
    oracle = _load_json(oracle_ablation_root / "summary.json")

    lines = [
        "# F1 R2 Attribution Ablation Report",
        "",
        f"- **Run root:** `{parent_dir}`",
        f"- **Model:** `claude-sonnet-4-5-20250929` (frozen Claude tools config)",
        f"- **Temperature:** 0.2",
        f"- **n:** 100 per condition (unless smoke)",
        "",
        "## Comparison table (Cert / Full)",
        "",
        "| Condition | Cert | Full | Failure stages |",
        "|-----------|-----:|-----:|----------------|",
    ]

    r1 = frozen.get("R1", {})
    if r1:
        lines.append(
            _comparison_row(
                "R1 (frozen)",
                cert=r1.get("certificate_valid_rate"),
                full=r1.get("fully_correct_rate"),
                failure_stages=r1.get("failure_stage_counts"),
            )
        )
    if oracle:
        lines.append(
            _comparison_row(
                "Oracle+Format (frozen ablation)",
                cert=oracle.get("certificate_valid_rate"),
                full=oracle.get("fully_correct_rate"),
                failure_stages=oracle.get("failure_stage_counts"),
            )
        )

    mode_order = [R2AttributionMode.R2A, R2AttributionMode.R2B, R2AttributionMode.R2C]
    by_mode = {row.get("r2_attribution_mode"): row for row in mode_summaries}
    for mode in mode_order:
        row = by_mode.get(mode.value)
        if row:
            lines.append(
                _comparison_row(
                    mode.value,
                    cert=row.get("certificate_valid_rate"),
                    full=row.get("fully_correct_rate"),
                    failure_stages=row.get("failure_stage_counts"),
                )
            )

    r2 = frozen.get("R2", {})
    if r2:
        lines.append(
            _comparison_row(
                "Frozen R2",
                cert=r2.get("certificate_valid_rate"),
                full=r2.get("fully_correct_rate"),
                failure_stages=r2.get("failure_stage_counts"),
            )
        )

    lines.extend(
        [
            "",
            "## Per-condition details",
            "",
        ]
    )

    for row in mode_summaries:
        mode = row.get("r2_attribution_mode", "?")
        fs = row.get("failure_stage_counts") or {}
        lines.extend(
            [
                f"### {mode} (`{row.get('ablation_condition')}`)",
                "",
                f"- Run dir: `{row.get('run_dir')}`",
                f"- extract={_format_rate(row.get('extractability_rate'))}, "
                f"verdict={_format_rate(row.get('verdict_accuracy'))}, "
                f"cert={_format_rate(row.get('certificate_valid_rate'))}, "
                f"full={_format_rate(row.get('fully_correct_rate'))}",
                f"- failure stages: not_extractable={fs.get('not_extractable', 0)}, "
                f"verdict_wrong={fs.get('verdict_wrong', 0)}, "
                f"certificate_invalid={fs.get('certificate_invalid', 0)}, "
                f"correct={fs.get('correct', 0)}",
                "",
            ]
        )

    r1_cert = r1.get("certificate_valid_rate")
    r2_full = r2.get("fully_correct_rate")
    r2a = by_mode.get("R2A", {})
    r2b = by_mode.get("R2B", {})
    r2c = by_mode.get("R2C", {})

    lines.extend(
        [
            "## Research questions",
            "",
            "1. **How much of the R2 gain survives when the model must construct the certificate itself?** "
            f"Compare R2A full={_format_rate(r2a.get('fully_correct_rate'))} and "
            f"R2B full={_format_rate(r2b.get('fully_correct_rate'))} vs frozen R2 full={_format_rate(r2_full)}.",
            "2. **How much improvement comes from validation only?** "
            f"R2A cert={_format_rate(r2a.get('certificate_valid_rate'))} vs R1 cert={_format_rate(r1_cert)}.",
            "3. **How much improvement comes from formatting repair only?** "
            f"R2B cert={_format_rate(r2b.get('certificate_valid_rate'))} vs R1 cert={_format_rate(r1_cert)}.",
            "4. **How much improvement requires certificate synthesis by the tool?** "
            f"R2C full={_format_rate(r2c.get('fully_correct_rate'))} minus max(R2A,R2B) full.",
            "5. **Which component accounts for most of the R1→R2 jump?** "
            "Compare deltas: validation (R2A−R1), repair (R2B−R1), synthesis (R2C−R2A/R2B), frozen R2−R1.",
            "",
            "## Division of labor (R2 decomposition)",
            "",
            "| Component | Role in R2 |",
            "|-----------|------------|",
            "| **Model** | Two-phase protocol: `tool_plan` then `final_submission`; decides verdict and (in R2A/R2B) constructs certificate content |",
            "| **Tool** | R2C: `solver.check_separation`, `solver.equivalence_certificate`, `solver.distinguishing_certificate` synthesize witnesses; R2A: validate only; R2B: format repair only |",
            "| **Verifier** | Independent `verify_f1_certificate` at scoring time (unchanged across conditions) |",
            "| **Certificate generator** | Oracle builders inside solver tools (R2C only); absent in R2A/R2B |",
            "",
            "## Notes",
            "",
            "- Frozen baselines are read from disk; this experiment does not re-run them.",
            "- R2C uses the same `_evaluate_item_with_tools` path as frozen F1 R2.",
            "- Do not modify frozen run directories.",
            "",
        ]
    )
    return "\n".join(lines)


def finalize_r2_attribution_mode_run(
    run_dir: Path,
    *,
    summary: dict[str, Any],
    cohort_id: str | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    """Write per-mode taxonomy and combined_summary for one R2 attribution cell."""
    run_dir = Path(run_dir)
    taxonomy_payload = analyze_failure_taxonomy(
        run_dir / SCORES_JSONL,
        run_dir / RESULTS_JSONL,
    )
    dump_json(run_dir / "certificate_failure_taxonomy.json", taxonomy_payload)

    track_row = {
        "model": summary.get("model"),
        "family": "F1",
        "track": summary.get("track"),
        "temperature": temperature,
        "cohort_id": cohort_id,
        "n": summary.get("n"),
        "extractability_rate": summary.get("extractability_rate"),
        "verdict_accuracy": summary.get("verdict_accuracy"),
        "certificate_valid_rate": summary.get("certificate_valid_rate"),
        "fully_correct_rate": summary.get("fully_correct_rate"),
        "failure_stage_counts": summary.get("failure_stage_counts"),
        "provider_error_count": summary.get("provider_error_count", 0),
        "status": "completed",
        "run_dir": str(run_dir),
        "ablation_condition": summary.get("ablation_condition"),
        "r2_attribution_mode": summary.get("r2_attribution_mode"),
    }
    combined = {
        "experiment": "r2_attribution_ablation",
        "ablation_condition": summary.get("ablation_condition"),
        "r2_attribution_mode": summary.get("r2_attribution_mode"),
        "models": [summary.get("model")],
        "families": ["F1"],
        "tracks": [summary.get("track")],
        "temperatures": [temperature] if temperature is not None else [],
        "max_items": summary.get("n"),
        "cohort_ids": {"F1": cohort_id} if cohort_id else {},
        "track_rows": [track_row],
        "cell_status_counts": {"completed": 1, "expected": 1},
    }
    dump_json(run_dir / "combined_summary.json", combined)

    report_lines = [
        f"# {summary.get('r2_attribution_mode')} run report",
        "",
        f"- Condition: `{summary.get('ablation_condition')}`",
        f"- n={summary.get('n')}",
        "",
        "## Metrics",
        "",
        f"- certificate_valid_rate: {_format_rate(summary.get('certificate_valid_rate'))}",
        f"- fully_correct_rate: {_format_rate(summary.get('fully_correct_rate'))}",
        "",
        "## Failure stages",
        "",
        format_failure_taxonomy_report(taxonomy_payload),
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
    return combined


def finalize_r2_attribution_study(
    parent_dir: Path,
    *,
    frozen_tools_root: Path,
    oracle_ablation_root: Path,
    cohort_id: str | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    """Aggregate R2A/R2B/R2C into parent combined_summary.json and report.md."""
    parent_dir = Path(parent_dir)
    mode_summaries: list[dict[str, Any]] = []
    track_rows: list[dict[str, Any]] = []

    for mode in R2AttributionMode:
        mode_dir = parent_dir / mode.value
        row = _mode_summary_row(mode_dir, mode)
        if row is None:
            continue
        mode_summaries.append(row)
        track_rows.append(
            {
                "model": row.get("model"),
                "family": "F1",
                "track": row.get("track"),
                "temperature": temperature,
                "cohort_id": cohort_id,
                "n": row.get("n"),
                "extractability_rate": row.get("extractability_rate"),
                "verdict_accuracy": row.get("verdict_accuracy"),
                "certificate_valid_rate": row.get("certificate_valid_rate"),
                "fully_correct_rate": row.get("fully_correct_rate"),
                "failure_stage_counts": row.get("failure_stage_counts"),
                "provider_error_count": row.get("provider_error_count", 0),
                "status": "completed",
                "run_dir": row.get("run_dir"),
                "ablation_condition": row.get("ablation_condition"),
                "r2_attribution_mode": mode.value,
            }
        )

    report = render_r2_attribution_comparison_report(
        parent_dir=parent_dir,
        mode_summaries=mode_summaries,
        frozen_tools_root=frozen_tools_root,
        oracle_ablation_root=oracle_ablation_root,
    )
    (parent_dir / "report.md").write_text(report, encoding="utf-8")

    combined = {
        "experiment": "r2_attribution_ablation",
        "models": [track_rows[0]["model"]] if track_rows else [],
        "families": ["F1"],
        "tracks": [row["track"] for row in track_rows],
        "temperatures": [temperature] if temperature is not None else [],
        "max_items": track_rows[0]["n"] if track_rows else None,
        "cohort_ids": {"F1": cohort_id} if cohort_id else {},
        "track_rows": track_rows,
        "cell_status_counts": {
            "completed": len(track_rows),
            "expected": len(R2AttributionMode),
        },
        "frozen_baselines": {
            "claude_tools": str(frozen_tools_root),
            "oracle_verdict_format_control": str(oracle_ablation_root),
        },
    }
    dump_json(parent_dir / "combined_summary.json", combined)
    return combined
